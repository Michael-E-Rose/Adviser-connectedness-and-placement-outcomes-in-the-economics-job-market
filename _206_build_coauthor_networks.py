#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Builds co-author networks from Scopus data for specific years with
inactive edges removed.
"""

from collections import Counter, defaultdict
from itertools import combinations, product
from pathlib import Path

import networkx as nx
import pandas as pd
from pybliometrics.scopus import ScopusSearch
from tqdm import tqdm

from _005_parse_students import write_stats

SOURCES_FILE = Path("./060_identifiers/CombesLinnemer.csv")
METRICS_FILE = Path("./161_author_metrics/metrics.csv")
TARGET_FOLDER = Path("./206_coauthor_networks/")
OUTPUT_FOLDER = Path("./990_output/")

DISCOUNT_FACTOR = 0.95
PUBLICATION_LAG = 1  # Add publications from this number of future years to each network
INACTIVE_PERIOD = 5  # Number of years after which we remove an author
LEAD_PERIOD = 2  # Number of years for centrality leads

_types = {'cp', 'ar', 're', 'no', 'sh', 'ip'}  # Document types we keep


def compute_global_statistics(H, G):
    """Return Series with network descriptives."""
    from statistics import mean, median
    s = pd.Series()
    total_size = nx.number_of_nodes(H)
    s["All Size"] = f"{total_size:,}"
    s["All Links"] = f"{nx.number_of_edges(H):,}"
    giant_size = nx.number_of_nodes(G)
    s["Giant Size"] = f"{giant_size:,}"
    s["Giant Share"] = f"{(giant_size/total_size):.2%}"
    s["Giant Diameter"] = f"{nx.diameter(G)}"
    eig = nx.eigenvector_centrality(G, weight="weight").values()
    s["Eigenvector Mean"] = round(mean(eig), 5)
    s["Eigenvector Median"] = median(eig)
    s["Eigenvector Max"] = round(max(eig), 3)
    return s


def get_network_years(col="academic_year"):
    """Get the years for which we need networks."""
    df = pd.read_csv(Path("./005_student_lists/main.csv"),
                     usecols=["stu_year", "academic_year"])
    df["academic_year"] = df["academic_year"].str.split("-").str[0].astype(int)
    return df[col].min()-1, df[col].max()+1


def get_publications(source_id, year, refresh=30, fields=("eid", "coverDate")):
    """Download list of relevant articles from Scopus."""
    q = f"SOURCE-ID({source_id}) AND PUBYEAR IS {year}"
    s = ScopusSearch(q, integrity_fields=fields, refresh=refresh)
    res = s.results or []
    return [p.author_ids.split(";") for p in res if
            p.coverDate and p.author_ids and p.subtype in _types]


def get_start_year():
    """Get year of first publication of oldest adviser."""
    df = pd.read_csv(METRICS_FILE, usecols=["year", "adv_experience"])
    df["diff"] = df["year"] - df["adv_experience"]
    return df["diff"].min()


def giant(G):
    """Return giant component of a network."""
    nodes = max(nx.connected_components(G), key=len)
    return G.subgraph(nodes).copy()


def main():
    # Read list of sources
    df = pd.read_csv(SOURCES_FILE).dropna(subset=["scopus_id"])
    n_journals = df.shape[0]
    sources = set(df["scopus_id"].astype("uint64").unique())
    n_journals_scopus = len(sources)
    sources.update(df["former_scopus_id"].dropna().astype("uint64").unique())
    del df

    # Collect edges
    min_year, max_year = get_network_years()
    pub_count = 0
    all_links = defaultdict(lambda: list())
    period = range(get_start_year(), max_year+PUBLICATION_LAG+1+LEAD_PERIOD)
    combs = list(product(sources, period))
    print(f">>> Obtaining publications for up to {len(combs):,} volumes of "
          f"{n_journals} different source IDs...")
    for source, year in tqdm(combs):
        pubs = get_publications(source, year)
        if year <= max_year+PUBLICATION_LAG:
            pub_count += len(pubs)
        for auths in pubs:
            all_links[year].extend(list(combinations(auths, 2)))

    # Generate networks
    print(">>> Generating networks...")
    out = pd.DataFrame()
    for net_year in range(min_year, max_year+1+LEAD_PERIOD):
        print(f"... using publications for {net_year}:")
        # Weigh edges
        print("... computing edge weights")
        edges = Counter()
        active = set()
        for year, links in all_links.items():
            if year > net_year+PUBLICATION_LAG:
                continue
            factor = DISCOUNT_FACTOR**(net_year-year+1)
            new = {(edge[0], edge[1]): weight*factor for edge, weight
                   in Counter(links).items()}
            edges.update(new)
            if year > net_year-INACTIVE_PERIOD:
                active.update([a for edge in links for a in edge])

        # Generate network
        print("... writing out")
        G = nx.Graph()
        edges = [(edge[0], edge[1], weight) for edge, weight in edges.items()]
        G.add_weighted_edges_from(edges)
        G = G.subgraph(active)
        ouf = (TARGET_FOLDER/str(net_year)).with_suffix(".gexf")
        nx.write_gexf(G, ouf)

        # Network statistics
        if net_year <= max_year+1:
            print("... calculating global statistics")
            s = compute_global_statistics(G, giant(G))
            s.name = net_year
            out = out.append(s)

    # Write global analysis
    print(">>> Finishing up")
    out = out[s.index]
    col_tuples = [tuple(c.split()) for c in out.columns]
    out.columns = pd.MultiIndex.from_tuples(col_tuples)
    fname = OUTPUT_FOLDER/"Tables"/"network_statistics.tex"
    out.to_latex(fname, multicolumn_format='c', column_format='lrr|rrr|rrr')

    # Write statistics
    print(f">>> Using {pub_count:,} different publications")
    write_stats({"N_of_publications": pub_count, "N_of_journals": n_journals,
                 "N_of_journals_scopus": n_journals_scopus})


if __name__ == '__main__':
    main()
