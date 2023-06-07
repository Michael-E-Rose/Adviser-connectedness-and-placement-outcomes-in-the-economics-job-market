#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Creates master file for regression in advisor-department network."""

from string import ascii_lowercase
from itertools import combinations_with_replacement as cwr
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from _680_create_centrality_masters import read_agg_centr

MAPPING_FILE = Path("./090_institution_data/mapping.csv")
ADVISERSTUDENT_MAP = Path("./199_adviser-student_map/actual.csv")
FACULTY_FILE = Path("./117_faculty_lists/hasselback.csv")
STUDENT_FILE = Path("./615_student_data/student.csv")
ADVISER_FILE = Path("./625_adviser_data/adviser.csv")
TARGET_FILE = Path("./880_distance_masters/adviser.csv")

CUNY = {"CUNY, BARUCH COLLEGE", "CUNY, BROOKLYN COLLEGE",
        "CUNY, HUNTER COLLEGE", "CUNY, QUEENS COLLEGE"}


def read_distance_files():
    """Read all distance files and stack on top of each other."""
    dist = {"coauthor": [], "citation": []}
    files = sorted(Path("./217_placement_distance/").glob("*.csv"))
    for file in tqdm(files):
        new = pd.read_csv(file, index_col=['university', 'adviser'])
        base, network, year = file.stem.split("_")
        new = new.add_prefix(network + "_")
        new["year"] = int(year)
        dist[network].append(new)
    coauthor = pd.concat(dist["coauthor"]).set_index("year", append=True)
    citation = pd.concat(dist["citation"]).set_index("year", append=True)
    df = coauthor.join(citation)
    rename = {"university": "plc_scopus", "adviser": "adv_scopus"}
    df = df.reset_index().rename(columns=rename)
    df["year"] = df["year"].astype("uint16")
    return df


def read_rankings():
    """Read our version of the rankings."""
    folder = Path("./401_institution_rankings")
    ranks = pd.read_csv(folder/"weighted.csv", encoding="utf")
    ranks["institution"] = ranks["institution"].astype(object)
    return (ranks.set_index(["institution", "year"])
                 .drop(columns="rank")
                 .add_suffix("-w"))


def main():
    # Read student file
    print(">>> Reading student data")
    cols = ["stu_id", "stu_school", "stu_year", "stu_plc", "plc_scopus"]
    df = pd.read_csv(STUDENT_FILE, usecols=cols, index_col=0)
    df = df.dropna(subset=["stu_plc"]).drop(columns="stu_plc")
    hiring = df["plc_scopus"].unique()
    df["stu_year"] = df["stu_year"].astype("uint16")
    df["stu_school"] = df["stu_school"].str.upper()
    adviser_map = pd.read_csv(ADVISERSTUDENT_MAP, index_col="stu_id",
                              usecols=["stu_id", "adv_scopus"])
    df = df.join(adviser_map)

    # Transform to adviser-placement information
    adv = df.reset_index()[["stu_id", "adv_scopus", "stu_year"]]
    adv = (adv.dropna(subset=['adv_scopus'])
              .set_index(['stu_id', 'stu_year'])
              ["adv_scopus"].str.split(";", expand=True)
              .stack().reset_index(level=2, drop=True)
              .reset_index()
              .rename(columns={0: 'adv_scopus'}))
    adv["adv_scopus"] = adv["adv_scopus"].astype("uint64")

    # Select best adviser
    cols = ['adv_scopus', 'year', 'adv_euclid', 'adv_experience']
    data = pd.read_csv(ADVISER_FILE, usecols=cols, index_col=[0, 1])
    data = data.dropna(subset=["adv_euclid"])
    best = (adv.join(data, how='left', on=['adv_scopus', 'stu_year'])
               .sort_values('adv_euclid', ascending=False)
               .groupby('stu_id').head(1))
    df = (df.drop("adv_scopus", axis=1)
            .merge(best[['stu_id', 'adv_scopus']], "inner",
                   left_index=True, right_on='stu_id')
            .set_index('stu_id'))

    # Read distance of each adviser to any department
    print(">>> Reading files with distance measures")
    dist = read_distance_files()

    # Merge placement ranks
    print(">>> Adding placement rankings...")
    ranks = read_rankings()
    dist = dist.join(ranks, on=["plc_scopus", "year"])
    rename = {"score-w": "plc_score-w", "year": "stu_year"}
    dist = dist.rename(columns=rename)
    n_unranked_plc = dist[dist["plc_score-w"].isnull()]["plc_scopus"].nunique()
    print(f"... {n_unranked_plc:,} placements (out of "
          f"{dist['plc_scopus'].nunique():,}) without rank for at least one year")
    dist["hiring"] = dist["plc_scopus"].isin(hiring)*1
    dist["hiring"] = dist["hiring"].astype(str).replace({"0": None})

    # Add placement indicator
    cols = ["adv_scopus", "stu_year", "plc_scopus"]
    movements = df[cols].apply(tuple, axis=1).values
    matrix = pd.DataFrame.from_records(movements).drop_duplicates()
    matrix.columns = cols
    # Drop adviser-years w/o known placements of their students
    dist = dist.join(matrix.set_index(cols[:2]), how="inner", on=cols[:2],
                     rsuffix="_")
    dist = (dist.drop_duplicates(subset=cols)
                .drop(columns="plc_scopus_"))
    matrix = matrix.dropna().set_index(cols)
    matrix["extensive"] = 1
    out = dist.join(matrix, how="left", on=cols)
    del dist, matrix

    # Merge adviser data
    out = out.join(data, how="inner", on=["adv_scopus", "stu_year"])
    del data
    best["stu_school"] = best["stu_id"].str.split(";").str[1].str.upper()
    adv_school = (best.sort_values(["adv_scopus", "stu_year"])
                      .groupby(["adv_scopus"])["stu_school"].first())
    out = out.join(adv_school, how="left", on="adv_scopus")

    # Add adviser centrality
    centr = read_agg_centr("coauthor")
    cols = ['adv_ev-w-win99-std', 'first_ev-w-win99-std_mean']
    centr = centr[cols]
    out = out.join(centr, how="left", on=["adv_scopus", "stu_year"])

    # Merge school ranks
    print(">>> Adding school rankings...")
    mapping = pd.read_csv(MAPPING_FILE, index_col="our_name")
    mapping.index = mapping.index.str.upper()
    mapping = (mapping.dropna().astype("uint64")
                      .rename(columns={"Scopus": "school_scopus"}))
    out = (out.join(mapping, on="stu_school")
              .drop(columns="stu_school"))
    out = out.join(ranks, on=["school_scopus", "stu_year"])
    out = out.rename(columns={"rank-w": "school_rank-w", "score-w": "school_score-w"})
    n_unranked_school = out[out["school_score-w"].isnull()]["school_scopus"].nunique()
    print(f"... {n_unranked_school:,} schools (out of "
          f"{out['school_scopus'].nunique():,}) without rank for at least one year")
    del ranks

    # School-specific variables
    mapping = mapping["school_scopus"].to_dict()
    schools = set(df["stu_school"].unique())
    schools.update({s.upper() for s in CUNY})
    schools.add("CLAREMONT MCKENNA COLLEGE")
    schools.remove("CLAREMONT GRADUATE UNIVERSITY")
    schools = {mapping[s] for s in schools}
    out['plc_phd'] = out['plc_scopus'].isin(schools)*1

    # Write out
    letters = ["".join(comb) for comb in cwr(ascii_lowercase, 3)]
    for col in ("plc_scopus", "school_scopus", "adv_scopus"):
        out[col] = pd.Categorical(out[col])
        out[col] = [letters[i] for i in out[col].cat.codes]
    out = out[~out["coauthor_d_dist"].isna()]
    print(f">>> Saving file with {out.shape[0]:,} observations and "
          f"{out['extensive'].sum():,.0f} positive incidences")
    out.to_csv(TARGET_FILE, index=False)
    print(">>> Share of missing values per variable:")
    print(out.isna().sum()/out.shape[0] * 100)


if __name__ == '__main__':
    main()
