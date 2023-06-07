#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Generates a yearly count of publications in journals used by the
Tilburg Economics Ranking, by institution.

For their methodology, please see https://econtop.uvt.nl/methodology.php.
"""

from itertools import product
from pathlib import Path

import pandas as pd
from pybliometrics.scopus import AffiliationRetrieval, ScopusSearch
from pybliometrics.scopus.exception import Scopus404Error
from tqdm import tqdm

SOURCE_FILE = Path("./060_identifiers/Tilburg.csv")
TARGET_FOLDER = Path("./401_institution_rankings/")

WINDOW = 5  # No. of years for rolling sum in ranking
START_YEAR = 1999
END_YEAR = 2020
_doc_types = ("ar", "re", "cp", "sh", "no")
_aff_types = ("univ", "coll")


def custom_long(df, value_name):
    """Melt wide DataFrame into a long list."""
    return (df.reset_index()
              .melt(id_vars='institution', var_name='year', value_name=value_name)
              .dropna()
              .sort_values(['institution', 'year']))


def get_affiliation_info(aff_id, refresh=False):
    """Get name and type of affiliation."""
    aff = AffiliationRetrieval(aff_id, refresh=refresh)
    return pd.Series((aff.affiliation_name, aff.org_type))


def read_sjr():
    """Read journal metrics file."""
    # Read in
    url = 'https://raw.githubusercontent.com/Michael-E-Rose/'\
          'SCImagoJournalRankIndicators/master/all.csv'
    sjr = pd.read_csv(url, usecols=['Sourceid', 'year', 'SJR'])
    sjr = sjr.drop_duplicates()
    sjr = sjr[sjr["SJR"] > 0]
    # Artificially extend journal impact factors
    min_year = sjr["year"].min()
    dummy = sjr[sjr["year"] == min_year].copy()
    for year in range(START_YEAR-WINDOW, END_YEAR+1):
        if year in sjr["year"].unique():
            continue
        dummy["year"] = year
        sjr = pd.concat([sjr, dummy])
    return sjr.reset_index(drop=True)


def main():
    # Read list of sources
    sources = pd.read_csv(SOURCE_FILE, encoding="utf8")['scopus_id'].values

    # Parse publication lists
    data = []
    years = range(1999-WINDOW, END_YEAR+1)
    combs = list(product(sources, years))
    print(f">>> Parsing {len(sources):,} journals during {len(years):,} years")
    for source_id, year in tqdm(combs):
        q = f'SOURCE-ID({source_id}) AND PUBYEAR IS {year}'
        res = ScopusSearch(q, refresh=50).results or []
        for p in res:
            if not p.afid or p.subtype not in _doc_types:
                continue
            for a in p.afid.split(";"):
                data.append((a, int(p.source_id), year))

    # Drop non-org affiliations
    pubs = pd.DataFrame.from_records(data, columns=["institution", "Sourceid", "year"])
    pubs = pubs[pubs["institution"].str.startswith("6")]

    # Count (weighted) publications
    print(">>> Counting (weighted) publications...")
    pubs = (pubs.merge(read_sjr(), "left", on=["Sourceid", "year"])
                .groupby(["institution", "year"]).agg(weighted=("SJR", "sum"),
                                                      unweighted=("SJR", "size"))
                .reset_index())

    # Collect institution information
    aff_ids = pubs["institution"].unique()
    aff_data = {}
    print(f">>> Collecting information on {len(aff_ids):,} institutions...")
    for aff_id in tqdm(aff_ids):
        aff_data[aff_id] = get_affiliation_info(aff_id)
    meta = pd.DataFrame(aff_data).T
    meta.columns = ["name", "type"]

    # Compute rolling sum and write out
    print(">>> Computing ranks...")
    for agg in ("unweighted", "weighted"):
        # Compute rolling sum
        scores = pubs.pivot_table(index="institution", columns="year",
                                  values=agg, aggfunc=sum)
        scores = (scores.rolling(WINDOW, axis=1, min_periods=0).sum()
                        .join(meta, on="institution")
                        .drop(columns="name"))

        # Subset to specific institution types
        scores["type"] = scores["type"].str.split("|").str[0]
        scores = scores[scores["type"].isin(_aff_types)].drop(columns="type")

        # Drop institution-years w/o publications
        if agg == "unweighted":
            mask_zero = scores == 0
        scores[mask_zero] = None

        # Rank institutions by year
        ranks = scores.rank(method="min", ascending=False)
        ranks = custom_long(ranks, "rank")
        ranks["rank"] = ranks["rank"].astype(int)
        scores = custom_long(scores, "score")

        # Write out
        out = ranks.merge(scores, on=['institution', 'year'])
        fname = (TARGET_FOLDER/agg).with_suffix(".csv")
        fformat = '%.3f'
        if agg == "unweighted":
            fformat = '%.0f'
        out.to_csv(fname, index=False, encoding="utf8", float_format=fformat)


if __name__ == '__main__':
    main()
