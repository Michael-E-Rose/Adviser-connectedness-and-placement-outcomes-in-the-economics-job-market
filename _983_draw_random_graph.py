#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Plots p values of many random regressions."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

mpl.use('Agg')
sns.set(style="whitegrid", font='Utopia')
plt.rc('axes', titlesize=20)
plt.rcParams["font.family"] = "serif"
plt.rcParams['font.serif'] = ['Utopia']

SOURCE_FOLDER = Path("./691_random_results/")
OUTPUT_FOLDER = Path("./990_output/")

OUR_VAL = 0.021


def make_p_graph(p_vals, our_pos, fname):
    """Plot sorted p values with ours highlighted."""
    fig, ax = plt.subplots(figsize=(7, 7))
    p_vals.plot(kind='scatter', x="share", y='p', ax=ax, s=40, ec='black',
                fc='none', marker='o')
    ax.set(ylabel="Estimated $p$ value", xlabel="Share of estimations (in %)")
    ax.set_yticks([0, 0.05, 0.1, 0.5, 1], minor=False)
    ax.set_xticks([0, 10, 25, 50, 75, 100], minor=False)
    ax.yaxis.grid(True, which='major')
    ax.xaxis.grid(True, which='major')
    plt.plot(our_pos/p_vals.shape[0]*100, OUR_VAL, marker='o', ms=6,
             mec='red', mfc='none')
    fig.savefig(fname, bbox_inches="tight")


def read_random_results(fname):
    """Read and format estimation results."""
    df = pd.read_csv(fname, index_col=0, nrows=3)
    df = (df.replace('"', '', regex=True).replace("=", "", regex=True)
            .apply(lambda s: pd.to_numeric(s, errors="coerce")))
    return df


def main():
    # Plot p values of regressions with distribution-based random assignment
    print(">>> Making plot for distribution-based assignment")
    df = pd.concat([read_random_results(d) for d in
                    SOURCE_FOLDER.glob("distribution*.csv")], axis=1)
    p_vals = df.iloc[-1].sort_values()
    our_pos = sum(p_vals <= OUR_VAL)
    print(f"... {our_pos/df.shape[1]:.1%} of values <= {OUR_VAL}, "
          f"{sum(p_vals <= 0.1)/df.shape[1]:.1%} of values <= 0.1")
    p_vals = p_vals.reset_index(drop=True).reset_index()
    p_vals["index"] += 1
    p_vals["index"] = p_vals["index"]/(p_vals.shape[0]) * 100
    p_vals.columns = ["share", "p"]
    fname = OUTPUT_FOLDER/"Figures"/"centrality_2sls_random-distribution.pdf"
    make_p_graph(p_vals, our_pos, fname)

    # Plot p values of regressions with distribution-based random assignment
    print(">>> Making plot for field-based assignment")
    df = read_random_results(SOURCE_FOLDER/"field.csv")
    p_vals = df.iloc[-1].sort_values()
    our_pos = sum(p_vals <= OUR_VAL)
    print(f"... {our_pos/df.shape[1]:.1%} of values <= {OUR_VAL}, "
          f"{sum(p_vals <= 0.1) / df.shape[1]:.1%} of values <= 0.1")
    p_vals = p_vals.reset_index(drop=True).reset_index()
    p_vals["index"] += 1
    p_vals["index"] = p_vals["index"]/(p_vals.shape[0]) * 100
    p_vals.columns = ["share", "p"]
    fname = OUTPUT_FOLDER/"Figures"/"centrality_2sls_random-field.pdf"
    make_p_graph(p_vals, our_pos, fname)


if __name__ == '__main__':
    main()
