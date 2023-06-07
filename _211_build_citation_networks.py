#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Builds weighted undirected citation networks."""

from collections import Counter, defaultdict
from itertools import product
from pathlib import Path
from time import sleep

import networkx as nx
import pandas as pd
from pybliometrics.scopus import AbstractRetrieval, ScopusSearch
from pybliometrics.scopus.exception import ScopusServerError, Scopus404Error
from requests.exceptions import ReadTimeout
from tqdm import tqdm

from _206_build_coauthor_networks import _types, get_network_years,\
    DISCOUNT_FACTOR, INACTIVE_PERIOD, PUBLICATION_LAG

SOURCES_FILE = Path("./060_identifiers/CombesLinnemer.csv")
TARGET_FOLDER = Path("./211_citation_networks/")


def get_cited_authors(eid, refresh=False):
    """Get Scopus Author IDs of authors cited by a document."""
    ab_full = robust_retrieval(eid, refresh=refresh)
    try:
        if len(ab_full.references) <= 40:
            ab_ref = robust_retrieval(eid, view="REF")
            authors = [ref.authors_auid.split(";") for ref
                       in ab_ref.references or []
                       if ref.type == 'resolvedReference' and ref.authors_auid]
        else:
            authors = []
            for ref in ab_full.references:
                try:
                    ab_new = robust_retrieval("2-s2.0-" + ref.id)
                    new_authors = [str(a.auid) for a in ab_new.authors]
                    authors.append(new_authors)
                except Scopus404Error:
                    continue
    except TypeError:  # No references given
        authors = []
    return authors


def robust_retrieval(eid, view="FULL", refresh=False):
    """Retrieve information on paper and references."""
    try:
        ab = AbstractRetrieval(eid, view=view, refresh=refresh)
    except UnicodeDecodeError:
        ab = AbstractRetrieval(eid, view=view, refresh=True)
    except (ReadTimeout, ScopusServerError):
        sleep(1.0)
        ab = AbstractRetrieval(eid, view=view, refresh=refresh)
    return ab


def main():
    # Read list of sources
    df = pd.read_csv(SOURCES_FILE).dropna(subset=["scopus_id"])
    n_journals = df.shape[0]
    sources = set(df["scopus_id"].astype("uint64").unique())
    sources.update(df["former_scopus_id"].dropna().astype("uint64").unique())
    del df

    # Collect edges
    min_year, max_year = get_network_years()
    period = range(1997, max_year + PUBLICATION_LAG + 1)
    combs = list(product(sources, period))
    print(f">>> Obtaining publications for up to {len(combs):,} volumes of "
          f"{n_journals} different source IDs...")
    all_links = defaultdict(lambda: list())
    for source_id, year in tqdm(combs):
        q = f"SOURCE-ID({source_id}) AND PUBYEAR IS {year}"
        if q in done:
            continue
        s = ScopusSearch(q, refresh=False)
        docs = s.results or []
        for p in docs:
            if p.subtype not in _types:
                continue
            try:
                citing_authors = p.author_ids.split(";")
            except AttributeError:
                continue
            auths = get_cited_authors(p.eid)
            for cited_authors in auths:
                all_links[year].extend(list(product(citing_authors, cited_authors)))

    # Generate networks
    print(">>> Generating networks...")
    for net_year in tqdm(range(min_year, max_year + 1)):
        # Weigh edges
        edges = Counter()
        active = set()
        for year, links in all_links.items():
            if year > net_year + 1:
                continue
            factor = DISCOUNT_FACTOR ** (net_year - year + 1)
            new = {(edge[0], edge[1]): weight * factor for edge, weight
                   in Counter(links).items()}
            edges.update(new)
            if year > net_year - INACTIVE_PERIOD:
                active.update([a for edge in links for a in edge])

        # Generate network
        G = nx.Graph()
        edges = [(edge[0], edge[1], weight) for edge, weight in edges.items()]
        G.add_weighted_edges_from(edges)
        G = G.subgraph(active)
        ouf = (TARGET_FOLDER/str(net_year)).with_suffix(".gexf")
        nx.write_gexf(G, ouf)


if __name__ == '__main__':
    main()
