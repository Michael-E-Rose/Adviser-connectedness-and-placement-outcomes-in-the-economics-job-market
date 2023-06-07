#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Plots centrality change of advisers with sufficient academic placements."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from _680_create_centrality_masters import read_agg_centr

sns.set(style="whitegrid", font='Utopia')
plt.rcParams["font.family"] = "serif"
plt.rcParams['font.serif'] = ['Utopia']

SOURCE_FILE = Path("./680_centrality_masters/master.csv")
OUTPUT_FOLDER = Path("./990_output/")

PLOT_CENTR = "adv_ev-w-win99-std"


def make_lineplots(df, fname, figsize=(13, 7)):
    """Make two plots showing the fluctuation of a value
    over time (rebased and relative).
    """
    # Initiate plot
    color = {a: "#bf94a6" for a in df["node"].unique()}
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=figsize)
    # Top plot: rebased values
    sns.lineplot(data=df, x="year", y="rebased", legend=False,
                 hue="node", linewidth=0.8, palette=color, ax=axes[0])
    axes[0].grid(axis="x")
    axes[0].set(ylabel="Rebased to 1999 (in %)")
    # Bottom plot: relative change
    sns.lineplot(data=df, x="year", y="delta", legend=False,
                 hue="node", linewidth=0.8, palette=color, ax=axes[1])
    axes[1].grid(axis="x")
    axes[1].set(xlabel="", ylabel="Year on year change (in %)",
                xlim=(df["year"].min(), df["year"].max()))
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def rebase(s):
    """Rebase series to its initial value."""
    return s/s.iloc[0]


def main():
    # Get relevant advisers
    cols = ['plc_year', 'adv_occ', 'best_adviser']
    df = pd.read_csv(SOURCE_FILE, usecols=cols, encoding="utf8")
    df = df[df['adv_occ'] > 1].drop(columns='adv_occ')
    adv = df["best_adviser"].str.strip("a").astype("uint64").unique()

    # Read centralities
    centr = read_agg_centr("coauthor").reset_index()
    centr = centr[centr["node"].isin(adv)][["node", "year", PLOT_CENTR]]
    centr = centr[centr["year"] <= 2006]

    # Compute differences
    centr["rebased"] = centr.groupby("node")[PLOT_CENTR].apply(rebase)
    centr["delta"] = centr.groupby("node")[PLOT_CENTR].diff()

    # Plot rebased value and first differences
    label = PLOT_CENTR.split("_", 1)[1].replace("-", "")
    fname = OUTPUT_FOLDER/"Figures"/f"line_{label}.pdf"
    make_lineplots(centr, fname)


if __name__ == '__main__':
    main()
