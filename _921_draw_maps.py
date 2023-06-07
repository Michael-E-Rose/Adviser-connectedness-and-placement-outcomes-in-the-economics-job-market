#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Draws placement networks on a map and computes reciprocity."""

from pathlib import Path

import cartopy
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
from math import sqrt

STUDENT_FILE = Path("./005_student_lists/main.csv")
PLACEMENT_FILE = Path("./020_placements/placements.csv")
COORDS_FILE = Path("./090_institution_data/geocoordinates.csv")
OUTPUT_FOLDER = Path("./990_output/")

_color = {'water': '#e3e3e3', 'land': '#e3e3e3', 'border': '#636463',
          'node': '#063687', 'edge': '#010a1b'}


def make_map(G, coords, fname, label=True):
    """Draw a map of North America with network on it."""
    # Initiate map
    fig = plt.figure()
    proj = ccrs.LambertConformal()
    ax = fig.add_subplot(1, 1, 1, projection=proj)
    ax.set_extent((-2_500_000, 2_500_000, -1_900_000, 1_900_000), crs=proj)
    # Draw coastlines, continents and borders
    ax.coastlines(linewidth=0.5, color=_color['border'])
    ax.add_feature(cartopy.feature.OCEAN, facecolor=_color['water'])
    ax.add_feature(cartopy.feature.LAND, color=_color['water'])
    ax.add_feature(cartopy.feature.BORDERS, edgecolor=_color['border'])
    fig.canvas.draw()
    # Node sizes
    nodelist = sorted(G.nodes())
    size = [int(v.get("size", 4))*3 for k, v in sorted(G.nodes(data=True))]
    # Map geographical coordinates to projection
    subset = coords.loc[nodelist]
    missing = list(subset[subset['lat'].isnull()].index)
    if missing:
        print(f"... {len(missing)} schools w/o coordinates: {'; '.join(missing)}")
    pos = {node: proj.transform_point(lng, lat, ccrs.PlateCarree())
           for node, (lat, lng) in subset.iterrows()}
    # Link weights
    weights = [sqrt(n[2]["weight"]) for n in sorted(G.edges(data=True))]
    # Draw network
    nx.draw_networkx(G, pos, nodelist=nodelist, node_size=size,
                     with_labels=False, edgelist=sorted(G.edges()),
                     width=weights, node_shape='o', node_color=_color['node'],
                     alpha=0.35, arrows=False, edge_color=_color['edge'])
    # Add annotation
    anno = f"{nx.number_of_nodes(G)} universities\n{sum(weights)} students"
    if label:
        plt.text(0.2*plt.xlim()[1], 0.625*plt.ylim()[1], anno, fontsize=12)
    # Write out
    plt.savefig(fname, bbox_inches='tight')
    plt.close()


def network_from_df(df):
    """Create a DiGraph from a DataFrame with weighted edges and node size
    according to number of occurrences.
    """
    nodes = df["stu_school"].value_counts().to_dict()
    movements = df[["stu_school", "stu_plc"]].apply(tuple, axis=1)
    edges = movements.value_counts().to_dict()
    G = nx.DiGraph()
    G.add_nodes_from(nodes.keys())
    G.add_node("Other")
    nx.set_node_attributes(G, {k: int(v) for k, v in nodes.items()}, "size")
    G.add_weighted_edges_from([(k[0], k[1], v) for k, v in edges.items()])
    return G


def main():
    students = pd.read_csv(STUDENT_FILE, index_col="stu_id",
                           usecols=["stu_id", "stu_school", "stu_jel"])
    placements = pd.read_csv(PLACEMENT_FILE, index_col="stu_id",
                             usecols=["stu_id", "stu_plc"])
    df = students.join(placements)
    df = df.dropna()

    # Mark placements outside the producing universities as Other
    mapping = {u: u for u in set(students["stu_school"])}
    df["stu_plc"] = df["stu_plc"].apply(lambda x: mapping.get(x, "Other"))

    # Plot network
    print(">>> Drawing placement network on map...")
    coords = pd.read_csv(COORDS_FILE, index_col=0)
    G = network_from_df(df)
    G.name = "all"
    G.remove_node("Other")
    outfile = OUTPUT_FOLDER/"Figures"/"map_placement.pdf"
    make_map(G, coords, outfile, label=False)

    # Check reciprocity
    links = [(u, v, d["weight"]) for (u, v, d) in G.edges(data=True)]
    df = pd.DataFrame(links, columns=["school", "placement", "students"])
    bidirectional = [(u, v) for (u, v) in G.edges() if u in G[v] and u != v]
    temp = pd.DataFrame(bidirectional, columns=["school", "placement"])
    temp["reciprocal"] = 1
    df = df.merge(temp, "left", on=["school", "placement"])
    df["reciprocal"] = df["reciprocal"].fillna(0)
    df["self"] = df.apply(lambda s: int(s["school"] == s["placement"]), axis=1)
    print(f">>> {df.shape[0]} non-zero links")
    n_reci = df[df["self"] != 1]["reciprocal"].mean()/2
    print(f"... {n_reci:.2%} of which are reciprocal")
    print(f"... and {df['self'].mean():.2%} of them are self-links")


if __name__ == '__main__':
    main()
