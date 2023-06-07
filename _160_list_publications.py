#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Lists publications for advisers and committee members with Scopus ID."""

from pathlib import Path

import pandas as pd
from pybliometrics.scopus import ScopusSearch
from tqdm import tqdm

ADVISERID_FILE = Path("./060_identifiers/advisers.csv")
TARGET_FILE = Path("./160_publication_list/advisers_committee.csv")

CUTOFF = 2016


def parse_publications(res):
    """Return EIDs, publication name (source) and publication year."""
    return [(p.eid, p.source_id, p.coverDate[:4]) for p in res
            if int(p.coverDate[:4]) < CUTOFF]


def perform_query(q, refresh=100):
    """Access ScopusSearch API to retrieve EIDs, sources and
    publication years.
    """
    try:
        res = ScopusSearch(q, refresh=refresh).results
        info = parse_publications(res)
    except (KeyError, TypeError):
        res = ScopusSearch(q, refresh=True).results
        info = parse_publications(res)
    if not info:
        return None, None, None
    eids, sources, years = zip(*info)
    return eids, sources, years


def main():
    # Advisers and committe members
    df = pd.read_csv(ADVISERID_FILE, usecols=['adv_scopus-name', 'adv_scopus'])
    df = df.dropna()
    scopus_ids = sorted(df['adv_scopus'].unique())
    print(f">>> Looking up {len(scopus_ids):,} researchers (advisers and "
          "committee)")

    # List Publications
    out = {}
    for auth_id in tqdm(scopus_ids):
        q = f"AU-ID({auth_id})"
        try:
            eids, sources, years = perform_query(q)
        except Exception as e:
            print(type(e), auth_id)
        if not eids or not sources or not years:
            print(f"{auth_id} has missing information")
            continue
        sources = [s or "-" for s in sources]  # Replace missing journal names
        out[auth_id] = {"eids": "|".join(eids), "sources": "|".join(sources),
                        "years": "|".join(years)}

    # Write out
    df = pd.DataFrame(out).T.sort_index()
    df.to_csv(TARGET_FILE, index_label="adv_scopus")


if __name__ == '__main__':
    main()
