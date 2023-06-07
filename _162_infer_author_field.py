#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Infers adviser's fields from their publications during 1995 and 2005."""

from pathlib import Path

import pandas as pd

SOURCE_FILE = Path("./160_publication_list/advisers_committee.csv")
JOURNAL_FILE = Path('./060_identifiers/CombesLinnemer.csv')
TARGET_FOLDER = Path("./162_author_fields/")

START = 1995
END = 2006


def find_mode(s, seed=42):
    """Return mode or random selection in case of equal frequency."""
    import random
    random.seed(seed)
    mode = s.mode()
    if len(mode) == 1:
        return mode.iloc[0]
    else:
        return random.choice(mode)[0]


def main():
    print(">>> Reading publications file and processing")
    df = pd.read_csv(SOURCE_FILE, usecols=["adv_scopus", "sources", "years"],
                     index_col="adv_scopus")
    df = df.apply(lambda s: s.str.split("|"), axis=1)

    years = df["years"].explode().to_frame("year")
    years["year"] = years["year"].astype("uint16")
    sources = df["sources"].explode().to_frame("source")

    df = pd.concat([sources, years], axis=1)
    df = df[df["year"].between(START, END)]
    df = df[df["source"] != "-"]
    df["source"] = df["source"].astype("uint64")

    # Merge fields information
    print(">>> Merging field information")
    cols = ["field", "scopus_id", "former_scopus_id"]
    fields_df = pd.read_csv(JOURNAL_FILE, usecols=cols).dropna(subset=["scopus_id"])
    fields = fields_df.set_index("scopus_id")[["field"]]
    former = (fields_df.dropna(subset=["former_scopus_id"])
                       .set_index("former_scopus_id"))
    fields = pd.concat([fields, former[["field"]]])
    df = df.join(fields, on="source")
    n_missing = df[df["field"].isna()]["source"].nunique()
    print(f"... no field information for {n_missing:,} distinct sources "
          f"({n_missing/df.shape[0]:.1%} of publications)")

    # Write out
    print(">>> Writing out")
    main_f = df[df["field"] != "Econ"]
    main_f = (main_f.dropna(subset=["field"])
                    .groupby(["adv_scopus"])["field"].apply(find_mode)
                    .apply(pd.Series).unstack()
                    .reset_index(level=0, drop=True)
                    .sort_index()
                    .dropna())
    main_f.name = "adv_jel"
    main_f.to_csv(TARGET_FOLDER/"main.csv")

    # Maintenance
    no_field = set(df.index.unique()) - set(main_f.index)
    print(f">>> No JEL code for {len(no_field):,} advisers or committee members")


if __name__ == '__main__':
    main()
