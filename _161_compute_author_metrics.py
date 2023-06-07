#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Crawls metrics for authors on a yearly basis: publications count, weighted
publication count, yearly citations and Euclidean index of citations.

You need a special API key by Scopus to access the citation view.
"""

from pathlib import Path

import pandas as pd
from numpy import inf, nan
from scholarmetrics import euclidean
from pybliometrics.scopus import CitationOverview
from tqdm import tqdm

from _160_list_publications import CUTOFF

SOURCE_FILE = Path("./160_publication_list/advisers_committee.csv")
TARGET_FILE = Path("./161_author_metrics/metrics.csv")


def compute_euclid(df):
    """Return yearly Euclidean index except when all entries are nan."""
    return df.dropna(how="all", axis=1).cumsum(axis=1).apply(euclidean)


def compute_fixed_growth(df, begin, end):
    """Compute growth rate between two fixed years."""
    try:
        lower = int(df.loc[df["year"] == begin, "adv_citestock"].values[0])
        upper = int(df.loc[df["year"] == end, "adv_citestock"].values[0])
        return (upper-lower)/lower
    except IndexError:
        return nan
    except ZeroDivisionError:
        return 0


def compute_growth(df, shift):
    """Compute growth rate relative to value `shift` periods away."""
    return df.pct_change(periods=shift)


def compute_rolling_change(df, window):
    """Compute percentage change to average of previous values."""
    return df/df.rolling(window=window, min_periods=0).mean().shift(window-1)


def get_yearly_citations(eid, pubyear, refresh=False):
    """Return dict of yearly citations."""
    scopus_id = eid.split("-")[-1]
    try:
        co = CitationOverview([scopus_id], start=pubyear, refresh=refresh)
    except Exception as e:
        co = CitationOverview([scopus_id], start=pubyear, refresh=True)
    return {y: int(c) for y, c in co.cc[0]}


def nan_preserving_sum(df):
    """Sum values except when all entries are nan."""
    return df.dropna(how="all", axis=1).fillna(0).sum(axis=0)


def main():
    # Read in
    print(">>> Reading publications file and processing")
    df = pd.read_csv(SOURCE_FILE, usecols=["adv_scopus", "eids", "years"],
                     index_col="adv_scopus")
    df = df.apply(lambda s: s.str.split("|"), axis=1)

    # Experience
    years = df["years"].explode().to_frame("year").reset_index()
    years["year"] = years["year"].astype("uint16")
    first = (years.sort_values("year")
                  .drop_duplicates("adv_scopus")
                  .rename(columns={"year": "first_pub_year"}))

    # Yearly citation count
    eids = [eid for sl in df["eids"] for eid in sl]
    pubyears = [pubyear for sl in df["years"] for pubyear in sl]
    eid_years = set(zip(eids, pubyears))
    print(f">>> Searching yearly citation counts for {len(eid_years):,} documents...")
    yearly_cites = {eid: get_yearly_citations(eid, pub_year) for
                    eid, pub_year in tqdm(eid_years)}
    print(">>> Computing citation counts")
    yearly_cites = pd.DataFrame(yearly_cites)
    yearly_cites = yearly_cites[yearly_cites.index < CUTOFF].T
    yearly_cites = yearly_cites[sorted(yearly_cites.columns)]
    eids = df["eids"].explode().to_frame("eid").reset_index()
    eid_cites = (eids.join(yearly_cites, on="eid")
                     .drop(columns="eid").set_index("adv_scopus"))
    grouped = eid_cites.groupby(eid_cites.index)
    cites = grouped.apply(nan_preserving_sum)
    cites = (cites.reset_index()
                  .rename(columns={"level_1": "year", 0: "citeflow"}))
    cites["adv_citestock"] = cites.groupby('adv_scopus')[["citeflow"]].cumsum()
    cites = cites.astype("uint64")

    # Citation growth measures
    print(">>> Computing citation growth measures")
    grouped_cites = cites.groupby("adv_scopus")
    # Growth of flow compared to average of previous years
    cites["citeflow_growth1"] = grouped_cites["citeflow"].pct_change()
    # Growth of stock compared previous years of different length
    for period in (1, 3):
        label = f"citestock_growth{period}"
        cites[label] = grouped_cites["adv_citestock"].apply(
            lambda df: compute_growth(df, period))
    cites = cites.replace([-inf, inf], nan)
    # Growth of stock and flow for entire periods
    fixed = grouped_cites.apply(lambda df: compute_fixed_growth(df, 1996, 1999))
    fixed = fixed.to_frame("citestock_growth9699")
    # Combine
    cites = cites.join(fixed, on="adv_scopus").fillna(0)
    cites = cites[sorted(cites.columns)]

    # Euclidean index of citations
    print(">>> Computing Euclidean indices of citation")
    euclid = grouped.apply(compute_euclid)
    euclid = (euclid.reset_index()
                    .rename(columns={"level_1": "year", 0: "adv_euclid"}))

    # Merge data
    print(">>> Merging data")
    out = euclid.merge(first, "left", on="adv_scopus")
    out["adv_experience"] = out["year"] - out["first_pub_year"].astype(int)
    out = out.drop(columns="first_pub_year")
    out = (out.merge(cites, "left", on=["adv_scopus", "year"])
              .sort_values(['adv_scopus', 'year']))

    # Write out
    print(">>> Writing out")
    out = out[out["year"].between(1997, CUTOFF)]
    out.to_csv(TARGET_FILE, index=False, float_format='%.5g')


if __name__ == '__main__':
    main()
