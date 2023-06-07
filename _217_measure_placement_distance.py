#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Measures social and citation distance between all advisers and all
universities, before and after deceased faculty members are removed.
"""

import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd
import networkx as nx
from tqdm import tqdm

from _005_parse_students import write_stats
from _215_compute_adviser_centralities import read_deceased

ADVISER_FILE = Path("./199_adviser-student_map/actual.csv")
DEATH_FILE = Path("075_deceased_authors/deceased.csv")
FACULTY_FILE = Path("./117_faculty_lists/hasselback.csv")
COAUTHOR_FOLDER = Path("./206_coauthor_networks/")
CITATION_FOLDER = Path("./211_citation_networks/")
TARGET_FOLDER = Path("./217_placement_distance/")

random.seed(0)


def count_social_distance(G, adv, nodes):
    """Return list of  social distances to all given nodes."""
    # Keep like this to ease possible expansion with names
    dist = []
    for member in nodes:
        if member == adv:  # Remove adviser
            continue
        try:
            new = len(nx.shortest_path(G, source=adv, target=member,
                      weight=None))
            dist.append(new)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
    return dist


def measure_faculty_distance(G, adv, faculty, year):
    """Return minimum social distance between adivser and any faculty."""
    out = {}
    for dep, members in faculty[year].items():
        distances = count_social_distance(G, adv, members)
        try:
            out[dep] = min(distances)
        except ValueError:
            out[dep] = None
    return pd.Series(out)


def melt_and_format(dist):
    """Melt distance matrix DataFrame and format columns."""
    out = pd.DataFrame.from_dict(dist).T.astype("float16")
    out.index.name = "adviser"
    out = (out.reset_index()
              .melt(id_vars="adviser", var_name="university", value_name="dist")
              .set_index(["university", "adviser"]))
    return out


def main():
    print(">>> Reading files")
    # Advisers with students
    df = pd.read_csv(ADVISER_FILE, usecols=["stu_id", "adv_scopus"])
    df = df.dropna(subset=['adv_scopus'])
    df["adv_scopus"] = df["adv_scopus"].str.split(";")
    all_adv = sorted(set([str(a) for sl in df['adv_scopus'] for a in sl]))

    # Deceased authors
    deaths = read_deceased()

    # Faculty-keyed dictionary
    hasselback = pd.read_csv(FACULTY_FILE, index_col="Scopus").drop(columns="country")
    hasselback = hasselback.fillna("").applymap(lambda c: set(c.split(";")))
    fac_lookup = hasselback.to_dict()

    # Compute distance to any faculty in co-author networks
    randomly_removed = set()
    all_nodes = {}
    print(f">>> Computing social distances")
    for f in COAUTHOR_FOLDER.glob("*.gexf"):
        year = f.stem
        if year not in fac_lookup.keys():
            continue

        # Read network
        G = nx.read_gexf(f)
        print(f"... for {year} with {G.number_of_nodes():,} nodes ...")
        degrees = dict(G.degree())
        all_nodes.update(G.nodes())
        nodes = defaultdict(lambda: list())
        for node, deg in dict(degrees).items():
            nodes[deg].append(node)
        G_orig = G.copy()

        # Social distance in normal networks
        print("... in normal networks")
        dist = {adv: measure_faculty_distance(G, adv, fac_lookup, year) for
                adv in tqdm(all_adv)}
        df_n = melt_and_format(dist)

        # Social distance without deceased authors
        print("... in networks w/o deceased authors")
        mask = deaths["death"] < datetime(int(year), 12, 31)
        deceased = deaths[mask].index
        G.remove_nodes_from(deceased)
        dist_d = {adv: measure_faculty_distance(G, adv, fac_lookup, year) for
                  adv in tqdm(all_adv)}
        df_d = melt_and_format(dist_d).add_prefix("d_")

        # Social distance with randomly removed authors
        print("... in networks w/o randomly removed authors")
        G = G_orig.copy()
        for auth in deceased:
            try:
                dec_degree = degrees[auth]
            except KeyError:
                continue
            picked = random.choices(nodes[dec_degree], k=1)[0]
            G.remove_node(picked)
            randomly_removed.add(picked)
        G.remove_nodes_from(randomly_removed)
        dist_r = {adv: measure_faculty_distance(G, adv, fac_lookup, year) for
                  adv in tqdm(all_adv)}
        df_r = melt_and_format(dist_r).add_prefix("r_")

        # Write out
        out = pd.concat([df_n, df_d, df_r], axis=1)
        mask_negative = out["d_dist"] < out["dist"]
        out.loc[mask_negative, "d_dist"] = out["dist"]
        fname = TARGET_FOLDER/f"adviser_coauthor_{year}.csv"
        out.to_csv(fname, float_format='%.0f')
        print("... file saved")

    # Compute distance to any faculty in citation networks
    print(f">>> Computing citation distances for {len(all_adv):,} advisers:")
    for f in sorted(CITATION_FOLDER.glob("*.gexf")):
        year = f.stem
        if year not in fac_lookup.keys():
            continue

        # Read network
        G = nx.read_gexf(f)
        print(f"... for {year} with {G.number_of_nodes():,} nodes ...")
        dist = {adv: measure_faculty_distance(G, adv, fac_lookup, year) for
                adv in tqdm(all_adv)}
        out = melt_and_format(dist)
        fname = TARGET_FOLDER/f"adviser_citation_{year}.csv"
        out.to_csv(fname, float_format='%.0f')
        print("... file saved")

    # Statistics
    all_members = set()
    for c in hasselback.columns:
        all_members.update({p for sl in hasselback[c].dropna().to_numpy() for p in sl})
    stats = {"N_of_Hasselback_Fac_Network": len(all_members.intersection(all_nodes))}
    write_stats(stats)


if __name__ == '__main__':
    main()
