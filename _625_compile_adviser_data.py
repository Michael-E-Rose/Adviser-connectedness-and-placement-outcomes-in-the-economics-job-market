#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Merges all adviser-related information."""

from pathlib import Path

import pandas as pd
from pybliometrics.scopus import AuthorRetrieval

REFERENCE_YEAR = 2003  # Year in which values for comparison table are computed

ADVISER_FILE = Path("./199_adviser-student_map/actual.csv")
METRICS_FILE = Path("./161_author_metrics/metrics.csv")
TARGET_FILE = Path("./625_adviser_data/adviser.csv")
OUTPUT_FOLDER = Path("./990_output/")


def get_adviser_name(auth_id, refresh=100):
    """Get Scopus author information for advisers."""
    au = AuthorRetrieval(auth_id, refresh=refresh)
    return " ".join([au.given_name, au.surname])


def make_top_table(df, fname, cutoff):
    """Produce table showing the top `cutoff` advisers."""
    # Fix table dimension
    top_adv = df[df["Rank"] <= cutoff].copy()
    top_adv["Rank"] = top_adv["Rank"].astype("uint8")
    top_adv = top_adv.reset_index()
    # Compute values
    top_adv["Name"] = top_adv['adv_scopus'].apply(get_adviser_name)
    top_adv["Euclid"] = top_adv["Euclid"].round(2)
    top_adv["Experience"] = top_adv["Experience"].astype("uint8")
    columns = ["Rank", "Name", "Students", "School", "Citations",
               "Euclid", "Experience"]
    top_adv = top_adv[columns]
    # Format rank
    top_adv = (top_adv.sort_values(["Rank", "Name"], ascending=True)
                      .rename(columns={"Rank": ""}))
    mask = top_adv[""].duplicated()
    top_adv.loc[mask, ""] = ""
    # Write out
    latex = top_adv.to_latex(escape=False, index=False).replace("llr", "lp{3cm}r|")
    fname.write_text(latex, encoding="utf8")


def main():
    # Map adviser to school
    stu = pd.read_csv(ADVISER_FILE, usecols=["stu_id", "adv_scopus"]).dropna()
    stu["stu_school"] = stu["stu_id"].str.split(";").str[1]
    stu = stu.set_index("stu_school")
    schools = (stu["adv_scopus"].str.split(";", expand=True)
                  .stack().to_frame("adv_scopus")
                  .droplevel(1).reset_index())
    schools["adv_scopus"] = schools["adv_scopus"].astype("uint64")

    # Merge adviser metrics
    metrics = pd.read_csv(METRICS_FILE)
    out = metrics[metrics["adv_scopus"].isin(schools["adv_scopus"].unique())]

    # Write out
    out = out.sort_values(["adv_scopus", "year"])
    out.to_csv(TARGET_FILE, index=False)

    # Correlation with number of students
    info = out[out["year"] == REFERENCE_YEAR].copy().set_index("adv_scopus")
    info["Students"] = schools["adv_scopus"].value_counts()
    rename = {'adv_euclid': 'Euclid', 'adv_citestock': 'Citations',
              'adv_experience': 'Experience'}
    info = info.rename(columns=rename)
    corr_vars = ["Citations", "Euclid", "Experience", "Students"]
    print(f">>> Spearman correlations of adviser characteristics ({REFERENCE_YEAR}):")
    print(info[corr_vars].corr("spearman").round(2))

    # Table of advisers with most students
    info["Rank"] = info["Students"].rank(method="min", ascending=False)
    schools = schools.drop_duplicates()
    schools["School"] = schools["stu_school"] + " & "
    schools = (schools.groupby("adv_scopus")["School"].sum()
                      .reset_index().set_index("adv_scopus"))
    info["School"] = schools["School"].str.strip(" & ")
    fname = OUTPUT_FOLDER/"Tables"/"advisers_most.tex"
    make_top_table(info, fname, cutoff=15)


if __name__ == '__main__':
    main()
