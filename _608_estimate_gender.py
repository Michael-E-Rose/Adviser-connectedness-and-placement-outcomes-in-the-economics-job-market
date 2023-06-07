#!/usr/bin/env python3
# Author:  Michael E. Rose <michael.ernst.rose@gmail.com>
"""Collect gender estimates for students from genderize.io.

This script was written for free usage of genderize, which
allows 1000 requests/day.  Run this script continuously on separate days
to obtain all the information.
"""

from collections import OrderedDict
from pathlib import Path

import pandas as pd
import genderize
from numpy import where
from tqdm import tqdm

from _005_parse_students import write_stats

STUDENT_FILE = Path("./005_student_lists/main.csv")
TARGET_FILE = Path("./608_gender_estimates/genderize.csv")


def clean_name(s):
    """Strip accents and remove interpunctuation."""
    import unicodedata
    new = s.replace(",", "").split("-")[0]
    return ''.join(c for c in unicodedata.normalize('NFD', new)
                   if unicodedata.category(c) != 'Mn')


def get_firstname(name):
    """Return first name."""
    try:
        firstnames = name.split(", ", 1)[1]
        new = clean_name(firstnames)
        firsts = [part for part in new.split(' ') if
                  len(part) > 1 and not part.endswith(".")]
        first = firsts[0]
        if first.endswith(".") and len(firstnames) > 1:
            first = firstnames[1]
        return first
    except IndexError:
        print(f">>> Firstname '{name}' will not produce results")
        return None


def main():
    # Read names of students and actually used advisers
    df = pd.read_csv(STUDENT_FILE, index_col=0, usecols=["stu_id", "Name"])

    # Skip persons that already have estimates
    try:
        collected = pd.read_csv(TARGET_FILE, index_col=0)
        collected = collected[collected.index.isin(df.index.tolist())]
        df = df.drop(collected.index, errors='ignore')
    except FileNotFoundError:
        collected = pd.DataFrame()

    # Prepare names
    df["first"] = df["Name"].apply(get_firstname)
    df = df.dropna(subset=['first'])

    # Get gender estimates
    estimates = OrderedDict()
    n_names = df['first'].nunique()
    print(f">>> Searching for {n_names:,} new names...")
    for name in tqdm(df["first"].unique(), total=n_names):
        try:
            resp = genderize.Genderize().get([name])
            estimates[name] = resp[0]
        except genderize.GenderizeException:  # Daily quota exceeded
            break

    # Write out
    if estimates:
        new = pd.DataFrame(estimates).T
        df = df.join(new, how="right", on="first")
        df = df[["count", "gender", "name", "probability"]]
        collected = pd.concat([collected, df]).sort_index()
        collected["count"] = collected["count"].fillna(0).astype(int).replace(0, "")
        collected.to_csv(TARGET_FILE, index_label="id")

    # Statistics
    counts = collected["gender"].value_counts()
    no_missing = collected["gender"].isnull().sum()
    total = collected.shape[0]
    print(f">>> No estimates for {no_missing} out of {total} "
          f"({no_missing/total:.2%}) persons")
    stats = {"N_of_gender_estimates": total - no_missing,
             "N_of_gender_missings": no_missing,
             "N_of_gender_male": counts["male"],
             "N_of_gender_female": counts["female"]}
    write_stats(stats)


if __name__ == '__main__':
    main()
