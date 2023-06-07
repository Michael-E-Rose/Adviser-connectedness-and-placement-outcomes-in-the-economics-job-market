#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Computes Eigenvector centralities of advisers' neighbors in
networks with them excluded.
"""

from datetime import datetime
from pathlib import Path

import networkx as nx
import pandas as pd
from tqdm import tqdm

from _005_parse_students import write_stats
from _206_build_coauthor_networks import giant

COAUTHOR_FOLDER = Path("./206_coauthor_networks")
TARGET_FOLDER = Path("./215_adviser_centralities")


def compute_centralities(H, G, degree=True):
    """Return DataFrame with node-wise network measures."""
    df = pd.DataFrame(index=sorted(H.nodes()))
    df["ev-w"] = pd.Series(
        nx.eigenvector_centrality(G, weight="weight", max_iter=200))
    # Winsorize
    level = 0.01
    label = f"ev-w-win{int((1-level)*100)}"
    df[label] = df[["ev-w"]].apply(lambda s: winsorize(s, level), axis=0)
    # Standardize
    standardized = df.apply(standardize).add_suffix("-std")
    df = df.join(standardized)
    # Degree
    if degree:
        df["deg"] = pd.Series(dict(nx.degree(H)))
    return df


def get_neighbors(H, node):
    """Find first-, second- and thrid-degree neighbors."""
    # First neighbors
    first_neigh = set(H.neighbors(node))
    # Second neighbors
    sec_neigh = set()
    for neigh in first_neigh:
        sec_neigh.update(set(H.neighbors(neigh)))
    sec_neigh -= set(first_neigh)
    sec_neigh -= {node}
    # Third neighbors
    third_neigh = set()
    for neigh in sec_neigh:
        third_neigh.update(set(H.neighbors(neigh)))
    third_neigh -= set(first_neigh)
    third_neigh -= set(sec_neigh)
    third_neigh -= {node}
    return first_neigh, sec_neigh, third_neigh


def number_to_word(num, letters=-2):
    """Turn a (slice of a )number to word, replacing hyphens."""
    from num2words import num2words
    return num2words(int(str(num)[letters:])).replace("-", "")


def read_adviser_ids(col='adv_scopus'):
    """Read sorted list of advisers."""
    advisers = pd.read_csv("./199_adviser-student_map/actual.csv")[col].dropna()
    advisers = set([a for sl in advisers.str.split(';') for a in sl])
    return sorted(advisers)


def read_deceased():
    """Read file with deceased authors and format."""
    deaths = pd.read_csv(Path("075_deceased_authors/deceased.csv"),
                         index_col="scopus_id")
    deaths.index = deaths.index.astype(str)
    deaths = deaths[deaths["death"] != "0"]
    deaths["death"] = pd.to_datetime(deaths["death"])
    return deaths


def standardize(s):
    """Standardize a DataFrame column."""
    return (s-s.mean())/s.std()


def winsorize(s, level=0.01):
    """Winsorize at specified level."""
    _min, _max = s.quantile([level, 1-level])
    return s.clip(lower=_min, upper=_max)


def main():
    files = sorted(COAUTHOR_FOLDER.glob("*.gexf"))
    advisers = set(read_adviser_ids())
    deaths = read_deceased()

    year_cutoff = 2005
    adv_network = set()
    adv_giant = set()

    print(f">>> Computing network variations for {len(advisers):,} advisers "
          f"in {len(files)} networks\n>>> Now working on:")
    for file in files:
        # Read in
        year = int(file.stem)
        print("...", year)
        cur_year = datetime(year, 1, 1)
        prev_year = datetime(year-1, 1, 1)
        new_deceased = deaths[deaths["death"].between(prev_year, cur_year)].index
        all_deceased = deaths[deaths["death"] < cur_year].index

        # Compute centralities
        start = datetime.now().replace(microsecond=0)
        H = nx.read_gexf(file)
        dfs = []
        cur_advisers = advisers.intersection(H.nodes())
        for adv in tqdm(cur_advisers):
            # Get neighbors
            first_neigh, sec_neigh, third_neigh = get_neighbors(H, adv)
            # Get number of deceased among neighbors
            dec = {'first_dec': len(first_neigh.intersection(new_deceased)),
                   'second_dec': len(sec_neigh.intersection(new_deceased)),
                   'third_dec': len(third_neigh.intersection(new_deceased))}
            dec = pd.DataFrame.from_dict(dec, orient="index")
            # Drop adviser
            H_reduced = H.copy()
            H_reduced.remove_node(adv)
            G = giant(H_reduced)
            # Refine neighbors
            first_neigh = list(first_neigh.intersection(G))
            sec_neigh = list(sec_neigh.intersection(G))
            if not first_neigh and not sec_neigh:
                continue
            # Compute centralities
            centr = compute_centralities(H_reduced, G)
            # Aggregate
            first = centr.loc[first_neigh].mean().to_frame().T.add_prefix("first_")
            second = centr.loc[sec_neigh].mean().to_frame().T.add_prefix("second_")
            # Append
            new = pd.concat([first, second], axis=1, sort=True).add_suffix("_mean")
            new = pd.concat([new, dec.T], axis=1)
            new.index = [adv]
            dfs.append(new)
        df = pd.concat(dfs)
        del dfs

        # Add adviser's own centrality
        G = giant(H)
        full = compute_centralities(H, G).add_prefix('adv_')
        df = df.join(full, how='left')

        # Add adviser's own centrality in network w/o deceased
        H.remove_nodes_from(all_deceased)
        G = giant(H)
        full_d = compute_centralities(H, G, degree=False)
        full_d = full_d.add_prefix('adv_').add_suffix("_d")
        df = df.join(full_d, how='left')

        # Statistics
        stats = {f"N_of_nodes_{number_to_word(year)}": nx.number_of_nodes(H),
                 f"N_of_nodes_{number_to_word(year)}_giant": nx.number_of_nodes(G)}
        write_stats(stats)
        if year <= year_cutoff:
            adv_network.update(cur_advisers)
            adv_giant.update(full.dropna(subset=['adv_ev-w']).index)

        # Write centralities
        fname = (TARGET_FOLDER/f"coauthor_{year}").with_suffix(".csv")
        df = df.sort_index()
        df.to_csv(fname, index_label="node", encoding="utf8")
        end = datetime.now().replace(microsecond=0)
        print("... elapsed time:", end-start)

    # Statistics on network membership
    adv_nonetwork = advisers - adv_network
    stats = {"N_of_advisers_nonetwork": len(adv_nonetwork),
             "N_of_advisers_nogiant": len(advisers - adv_giant - adv_nonetwork)}
    write_stats(stats)


if __name__ == '__main__':
    main()
