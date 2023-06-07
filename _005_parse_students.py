#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Combines and filters dissertation lists."""

from pathlib import Path

import pandas as pd

SOURCE_FILE = Path("./001_students/main.tab")
TARGET_FILE = Path("./005_student_lists/main.csv")
OUTPUT_FOLDER = Path("./990_output/")

ACADEMIC_YEARS = ('2000-2001', '2001-2002', '2002-2003', '2003-2004')


def write_stats(stat_dct):
    """Write out textfiles as "filename: content" pair."""
    from pathlib import Path
    for key, val in stat_dct.items():
        fname = Path("990_output", "Statistics", key).with_suffix(".txt")
        fname.write_text(f"{int(val):,}")


def main():
    # Read in
    df = pd.read_csv(SOURCE_FILE, index_col="ID", dtype={"Scopus_ID": "object"}, sep="\t")
    df = df.dropna(subset=['Name'])
    df['Year'] = df['Year'].astype(int)
    df = df[df["academic_year"].isin(ACADEMIC_YEARS)]
    df = df[df['Year'] >= min([int(x.split('-')[0]) for x in ACADEMIC_YEARS])]
    nphds1 = df.shape[0]
    nunis1 = df['University'].nunique()

    # Drop students in Q (Agriculture)
    print(f">>> Dropping {sum(df['JEL'] == 'Q')} students in Q")
    df = df[df["JEL"] != "Q"]

    # Cross-tabulation
    f = OUTPUT_FOLDER/"Tables"/"phd_crosstab.tex"
    c = pd.crosstab(df['Year'], df['JEL'], margins=True)
    c.to_latex(f)

    # Main file
    rename = {"University": "stu_school", "Year": "stu_year", "JEL": "stu_jel",
              "Scopus_ID": "stu_scopus", "repec_handle": "stu_repec"}
    df = df.rename(columns=rename).sort_values(['stu_year', 'stu_school', 'Name'])
    df.to_csv(TARGET_FILE, index_label="stu_id")

    # Statistics
    stats = {'N_of_PhDsOld': nphds1, 'N_of_PhDs': df.shape[0],
             'N_of_UnisOld': nunis1, 'N_of_Unis': df['stu_school'].nunique()}
    write_stats(stats)
    print(">>> Distribution by JEL-Code\n", df["stu_jel"].value_counts())
    print(">>> Distribution by Year\n", df["stu_year"].value_counts())


if __name__ == '__main__':
    main()
