#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Plots minimum social distance between adviser and placement
in year of student's placement.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
import seaborn as sns
from numpy import nan
from tqdm import tqdm

SOURCE_FILE = Path("./680_centrality_masters/master.csv")
FACULTY_FILE = Path("./117_faculty_lists/hasselback.csv")
ADVISER_FILE = Path("./199_adviser-student_map/actual.csv")
NETWORK_FOLDER = Path("./206_coauthor_networks/")
OUTPUT_FOLDER = Path("./990_output/")

mpl.use('Agg')
sns.set(style="whitegrid", font='Utopia')
plt.rcParams["font.family"] = "serif"
plt.rcParams['font.serif'] = ['Utopia']
tqdm.pandas()


def adviser_placement_distance(s, networks):
    """Measure minimum social distance between adivsor and faculty at
    student's placement for all networks.
    """
    colleagues = s["plc_faculty"]
    year = s["plc_year"]
    d = {"adv_dist": None, "com_dist": None}
    G = networks[year]
    d["adv_dist"] = get_minimum_distance(G, s["adv_scopus"], colleagues)
    try:
        d["com_dist"] = get_minimum_distance(G, s["comm_scopus"], colleagues)
    except TypeError:
        pass
    return pd.Series(d)


def make_histogram(s, fname):
    """Make and save histogram with KDE for share."""
    adv_dist = s["adv_dist"].dropna()
    adv_n = len(adv_dist)
    adv_levels = len(adv_dist.unique())
    adv_mean = adv_dist.mean()
    com_dist = s["com_dist"].dropna()
    com_n = len(com_dist)
    com_levels = len(com_dist.unique())
    com_mean = com_dist.mean()
    # Fake plot to get axis labels (only useful when kde=True)
    # fig2, ax2 = plt.subplots()  # Fake to get axis labels
    # sns.distplot(com_dist, kde=False, ax=ax2)
    # sns.distplot(com_dist, kde=False, ax=ax2)
    # y_ticks = [int(t) for t in ax2.get_yticks()]
    plt.clf()
    # Real plot without KDE
    fig, ax = plt.subplots()
    sns.histplot(adv_dist, kde=False, bins=adv_levels, ax=ax)
    sns.histplot(com_dist, color='g', kde=False, bins=com_levels, ax=ax)
    plt.xlim([1, adv_levels])
    plt.axvline(adv_mean, color='b', linestyle='dashed', linewidth=2)
    plt.axvline(com_mean, color='g', linestyle='dashed', linewidth=2)
    # ax.set_yticklabels(y_ticks)
    plt.xticks(list(plt.xticks()[0])[1:] + [1])
    ax.set_xlabel("Social distance to nearest placement faculty member")
    ax.set_ylabel("Number of students")
    plt.text(0.7*plt.xlim()[1], 0.89*plt.ylim()[1], f"Adviser; N = {adv_n}",
             fontsize=12, color='b')
    plt.text(0.7*plt.xlim()[1], 0.81*plt.ylim()[1], f"Committee; N = {com_n}",
             fontsize=12, color='g')
    sns.despine()
    fpath = (OUTPUT_FOLDER/"Figures"/fname).with_suffix(".pdf")
    plt.savefig(fpath, bbox_inches="tight")
    # Plot distance with advisers on top of this
    plt.clf()


def get_faculty(s, lookup):
    """Return list of faculty members for a given year, alternatively
    the preceding year, alternatively the following year.
    """
    dep = s["plc_scopus"]
    year = s["plc_year"]
    yearly_faculty = lookup.get(year)
    if yearly_faculty is None:
        return None  # facilitates dropping
    colleagues = yearly_faculty.get(dep)
    return colleagues


def get_minimum_distance(G, sources, targets):
    """Measure distance between group of source nodes and target nodes."""
    distances = []
    for node1 in sources:
        node1 = str(int(node1))
        for node2 in targets:
            try:
                new = len(nx.shortest_path(G, source=node1, target=node2,
                          weight=None))
            except Exception as e:  # either node not in graph or no path between them
                continue
            distances.append(new)
    try:
        return sorted(distances)[0]
    except IndexError:
        return None


def read_networks():
    """Read networkx files and return nested dictionary."""
    networks = {}
    for f in tqdm(sorted(NETWORK_FOLDER.glob("*.gexf"))):
        G = nx.read_gexf(f)
        year = f.stem
        G.name = year
        networks[year] = G
    return networks


def main():
    # Read student data
    cols = ["stu_id", "plc_scopus", "plc_year", "plc_type"]
    df = pd.read_csv(SOURCE_FILE, index_col="stu_id", usecols=cols)
    df = df.dropna(subset=["plc_year", "plc_scopus"], how="any")
    df["plc_year"] = df["plc_year"].astype(int).astype(str)

    # Merge committee members
    adv = pd.read_csv(ADVISER_FILE, index_col="stu_id",
                      usecols=["stu_id", "adv_scopus", "comm_scopus"])
    for col in ["adv_scopus", 'comm_scopus']:
        adv[col] = adv[col].str.split(";")
    df = df.join(adv, how="inner")

    # Read faculty file
    hasselback = pd.read_csv(FACULTY_FILE, index_col="Scopus").drop(columns="country")
    hasselback = hasselback.fillna("").applymap(lambda c: set(c.split(";")))
    fac_lookup = hasselback.to_dict()

    # Get faculty at placement
    df["plc_faculty"] = df.apply(lambda s: get_faculty(s, fac_lookup), axis=1)
    before = df.shape[0]
    missing = df[df["plc_faculty"].isnull()]
    df = df.dropna(subset=["plc_faculty"])
    after = df.shape[0]
    print(f">>> Dropping {before-after:,} students because faculty data is "
          "missing for their placements")

    # Measure minimum social distance
    print(">>> Computing social distances...")
    networks = read_networks()
    df = df.reset_index().set_index(["stu_id", "plc_scopus", "plc_type"])
    dist = df.apply(lambda s: adviser_placement_distance(s, networks), axis=1)
    print(f"Means: {dist['adv_dist'].mean():.2} (advisers) and "
          f"{dist['com_dist'].mean():.2} (committee members)")
    make_histogram(dist, "hist_dist-coauth_adv-plc")

    # Sensitivity
    no_dist = dist[dist["adv_dist"].isna()].reset_index().set_index("stu_id")
    print(f">>> {dist.dropna(how='all').shape[0]:,} students with social "
          f"distance, {no_dist.shape[0]:,} without")
    print(">>> Distribution of placement types:")
    print(no_dist["plc_type"].value_counts())


if __name__ == '__main__':
    main()
