#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Plots median differences of advisers included and not included in final
data using data as of 2003.
"""

from itertools import product
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from numpy import median
from scipy.stats import median_test

from _625_compile_adviser_data import REFERENCE_YEAR

MAPPING_FILE = Path("./090_institution_data/mapping.csv")
ADVSTU_FOLDER = Path("./199_adviser-student_map/")
CENTRALITY_FOLDER = Path("./215_adviser_centralities/")
RANK_FILE = Path("./401_institution_rankings/weighted.csv")
DATA_FILE = Path("./625_adviser_data/adviser.csv")
MASTER_FILE = Path("./680_centrality_masters/master.csv")
OUTPUT_FOLDER = Path("./990_output/")

mpl.use('Agg')
sns.set(style="whitegrid", font='Utopia')
plt.rc('axes', titlesize=20)


def find_university(df):
    """Find university as of `YEAR` or most common one."""
    try:
        current = df[df["year"] == REFERENCE_YEAR]["university"].iloc[-1]
        return current
    except IndexError:
        return df["university"].mode().values[-1]


def p_to_stars(p, thres=(0.1, 0.05, 0.01)):
    """Return stars for significance values."""
    n_stars = len([t for t in thres if p < t])
    return "".join("*"*n_stars)


def plot_differences(df, fname, cols, diff_var, ncols, nrows, figsize=(15, 10)):
    """Plot barplots showing differences betweens advisers with one
    or more placed students.
    """
    # Subset for significance computation
    single = df[df[diff_var] == "> 1"]
    multiple = df[df[diff_var] != "<= 1"]
    # Plot
    fig, axes = plt.subplots(nrows, ncols, sharex=True, sharey=False,
                             figsize=figsize)
    grid = list(product(range(0, nrows), range(0, ncols)))
    for i, col in enumerate(cols):
        idx_1, idx_2 = grid[i]
        ax = axes[idx_1][idx_2]
        sns.barplot(x=diff_var, y=col, data=df, ax=ax, estimator=median)
        if idx_1 == 0:
            ax.set_xlabel("")
        ax.set(ylabel="", title=col)
        # T-test
        t = median_test(single[col], multiple[col])
        stars = p_to_stars(t[1])
        x = 0.45
        y = 0.85*ax.get_ylim()[1]
        ax.annotate(stars, (x, y), fontsize=12)
    # Save
    plt.savefig(fname, bbox_inches="tight")
    plt.close(fig)


def main():
    # Read master file
    cols = ["best_adviser", "adv_occ"]
    df = pd.read_csv(MASTER_FILE, usecols=cols)
    df["best_adviser"] = df["best_adviser"].str.replace("a", "").astype("uint64")

    # Create dataset by adviser status
    adv_many = set(df[df["adv_occ"] > 1]["best_adviser"].unique())
    adv_one = set(df[df["adv_occ"] <= 1]["best_adviser"].unique())
    adv = pd.concat([pd.DataFrame(index=adv_many, data=["> 1"]*len(adv_many)),
                     pd.DataFrame(index=adv_one, data=["<=1"]*len(adv_one))])
    label = "# students placed academically in diff. years"
    adv.columns = [label]

    # Add data as of YEAR
    data_cols = ["adv_scopus", "adv_experience", "adv_euclid", "year"]
    data = pd.read_csv(DATA_FILE, index_col="adv_scopus", usecols=data_cols)
    data = data[data["year"] == REFERENCE_YEAR].drop(columns="year")
    centr_cols = ["node", "adv_ev-w", "adv_deg", "first_ev-w_mean"]
    centr = pd.read_csv(CENTRALITY_FOLDER/f"coauthor_{REFERENCE_YEAR}.csv",
                        index_col="node", usecols=centr_cols)
    adv = (adv.join(data)
              .join(centr)
              .fillna(0))

    # Find adviser's university
    adv_actual = pd.read_csv(ADVSTU_FOLDER/"actual.csv", index_col="stu_id",
                             usecols=["stu_id", "adv_scopus"])
    adv_actual = adv_actual["adv_scopus"].str.split(";").explode()
    adv_actual = (adv_actual.dropna().astype("uint64")
                            .reset_index().set_index("adv_scopus"))
    adv_actual = adv_actual["stu_id"].str.split(";", expand=True)
    adv_actual.columns = ["name", "university", "year"]
    adv_actual = adv_actual.drop(columns="name").reset_index()
    adv_actual["year"] = adv_actual["year"].astype("uint16")
    university = adv_actual.groupby("adv_scopus").apply(find_university)

    # Add school rank
    mapping = pd.read_csv(MAPPING_FILE, index_col="our_name")
    university = (university.to_frame("university")
                            .join(mapping, on="university")
                            .drop(columns="university")
                            .rename(columns={"Scopus": "univ_scopus"}))
    assert university["univ_scopus"].isna().sum() == 0
    ranks = pd.read_csv(RANK_FILE, index_col=0)
    ranks = ranks[ranks["year"] == REFERENCE_YEAR].drop(columns="year")
    university = (university.join(ranks, on="univ_scopus")
                            .drop(columns="univ_scopus"))
    adv = adv.join(university)

    # Make plot
    rename = {"score": "School score", "adv_experience": "Experience",
              "adv_euclid": "Euclidean index", "adv_ev-w": "Eigenvector",
              "adv_deg": "Degree", "first_ev-w_mean": "Coauthors' mean EV"}
    adv = adv.rename(columns=rename)
    plot_vars = ["School score", "Experience", "Euclidean index",
                 "Eigenvector", "Coauthors' mean EV", "Degree"]
    fname = OUTPUT_FOLDER/"Figures"/"bar_adv_comparison.pdf"
    plot_differences(adv, fname, plot_vars, label, ncols=3, nrows=2)


if __name__ == '__main__':
    main()
