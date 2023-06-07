#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Maps students to their advisers and committee members."""

import random
from collections import Counter
from pathlib import Path
from random import choices

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from numpy import arange
from tqdm import tqdm

from _005_parse_students import write_stats

STUDENT_FILE = Path("./005_student_lists/main.csv")
REPEC_FILE = Path("./050_adviser_genealogy.repec/repec.csv")
MANUAL_FILE = Path("./055_manual_advisers/adviser_list.csv")
ID_FILE = Path("./060_identifiers/advisers.csv")
FIELD_FILE = Path("./162_author_fields/main.csv")
TARGET_FOLDER = Path("./199_adviser-student_map/")
OUTPUT_FOLDER = Path("./990_output/")

font = {'family': 'serif', 'serif': 'Utopia', 'size': 15}
mpl.use("Agg")
mpl.rc('font', **font)
plt.rc('axes', titlesize=20)
mpl.rcParams['axes.unicode_minus'] = False


def add_ids(df, scopus, source, target):
    """Merge Scopus IDs to individuals."""
    return (df[source].str.split("; ", expand=True)
              .stack().dropna()
              .reset_index(level=1, drop=True).reset_index()
              .drop_duplicates(subset=["stu_id", 0])
              .join(scopus, on=0)
              .rename(columns={0: source.split("_")[0], 'Scopus_ID': target}))


def aggregate(df):
    """Aggregate duplicated DataFrame by joining their string entries."""
    for col in df.columns[1:]:
        try:
            df[col] = df[col].astype("uint64").astype(str) + ";"
        except ValueError:
            df[col] = df[col].astype(str) + ";"
    df = df.groupby('stu_id').sum()
    for col in df.columns:
        df[col] = df[col].str.strip(";")
    return df


def make_histogram(counter, fname, width=1):
    """Save a histogram made from Counter object."""
    counted_values = Counter(counter.values())
    m = max(counted_values.keys())
    labels = list(range(1, m+1))
    counts = [Counter(counter.values()).get(i, 0) for i in labels]
    indexes = arange(len(labels))
    # Make plot
    fig, ax = plt.subplots()
    ax.bar(indexes, counts, width, align="edge")
    # Add ticks for for non-zero counts
    plt.xticks(indexes + width * 0.5, labels, rotation=20)
    for i in [i-1 for i in range(1, m+1) if i not in counted_values]:
        ax.xaxis.get_major_ticks()[i].set_visible(False)
    # Add number of observations
    n = sum(counted_values.values())
    plt.text(0.8*plt.xlim()[1], 0.85*plt.ylim()[1], f"N = {n:,}", fontsize=12)
    # Save figure
    ax.set(xlabel="Number of students per adviser", ylabel="Incidence")
    ax.xaxis.grid(False)
    plt.savefig(fname, bbox_inches="tight")
    plt.close()


def main():
    # Manually collected advisers
    manual_cols = ["stu_id", "adviser_name", "commitee_members", "source"]
    manual = pd.read_csv(MANUAL_FILE, index_col="stu_id", usecols=manual_cols,
                         encoding="utf8")

    # Advisers from RePEc
    repec = pd.read_csv(REPEC_FILE, encoding="utf8", index_col=0,
                        usecols=["stu_id", "adviser_name"])
    repec = repec.dropna(subset=["adviser_name"])
    repec["source"] = "genealogy.repec"
    df = repec.join(manual, how="outer", lsuffix="_x", rsuffix="_y")
    df["adviser_name"] = df[["adviser_name_x", "adviser_name_y"]].apply(
        lambda x: x.str.cat(sep='; '), axis=1)
    df = df.drop(columns=["adviser_name_x", "adviser_name_y", "source_x", "source_y"])
    df = df[df['adviser_name'] != ""]

    # Add Scopus IDs of Advisers
    scopus = pd.read_csv(ID_FILE, index_col="adv")[["adv_scopus"]]
    advisers = add_ids(df.copy(), scopus, 'adviser_name', 'adv_scopus')
    advisers = advisers.drop_duplicates(subset=["stu_id", "adv_scopus"])
    no_scopus = set(advisers[advisers['adv_scopus'].isnull()]['adviser'])
    advisers = aggregate(advisers.dropna(subset=['adv_scopus']).copy())
    df = df.join(advisers)

    # Add Scopus IDs of Committee members
    comm = add_ids(df.copy(), scopus, 'commitee_members', 'adv_scopus')
    comm = comm.rename(columns={"adv_scopus": "comm_scopus"})
    no_scopus.update(comm[comm['comm_scopus'].isnull()]['commitee'].unique())
    comm = aggregate(comm.dropna(subset=['comm_scopus']).copy())
    df = df.join(comm)

    # Write out
    df = (df.drop(['adviser_name', 'commitee'], axis=1)
            .rename(columns={"adviser": "adviser_name"}))
    df.to_csv(TARGET_FOLDER/"actual.csv", encoding="utf8")

    # Histogram for number of students
    advisers = [a for sl in df["adv_scopus"].str.split(";").dropna()
                for a in sl]
    adviser_counter = Counter(advisers)
    fname = OUTPUT_FOLDER/"Figures"/"hist_adv_numstudents.pdf"
    make_histogram(adviser_counter, fname)

    # Maintenance
    stu_data = pd.read_csv(STUDENT_FILE, index_col="stu_id")
    no_adviser = set(stu_data.index) - set(df[df["adviser_name"] != ""].index)

    # Statistics
    print(f">>> No adviser for {len(no_adviser)} students")
    stats = {'N_of_PhDs_with_adviser': (df["adviser_name"] != "").sum(),
             'N_of_PhDs_without_adviser': len(no_adviser),
             'N_of_advisers': len(adviser_counter)}
    write_stats(stats)

    # Randomize with same student-per-adviser distribution
    distribution = Counter(adviser_counter.values())
    students = df.index
    advisers = list(adviser_counter.keys())
    n_max = max(distribution.keys())
    max_adv = [a for a, v in adviser_counter.items() if v == n_max][0]
    combs = []
    print(">>> Creating random states for each adviser as most common adviser")
    for a in tqdm(advisers):
        if a == max_adv:
            continue
        temp_advisers = advisers.copy()
        temp_advisers.remove(a)
        temp_students = students.copy()
        picks = choices(temp_students, k=n_max)
        new = [(a, p) for p in picks]
        temp_students = temp_students.drop(picks)
        for size, n_advisers in distribution.items():
            if size == 1 or size == n_max:
                continue
            for idx in range(n_advisers):
                new_a = random.choice(temp_advisers)
                temp_advisers.remove(new_a)
                picks = choices(temp_students, k=size)
                temp_students = temp_students.drop(picks)
                new.extend((new_a, p) for p in picks)
        # Finalize
        combs.append(new)
    # Write out
    print("... picking 500 states at random:")
    for i, assignments in tqdm(enumerate(choices(combs, k=500))):
        fname = TARGET_FOLDER/f"random_distribution{i:03d}.csv"
        df = pd.DataFrame(assignments, columns=["random", "stu_id"])
        df = df.sort_values("stu_id")
        df.to_csv(fname, index=False)

    # Randomize within field
    adv_field = pd.DataFrame(index=advisers)
    adv_field.index.name = "adv_scopus"
    fields = pd.read_csv(FIELD_FILE, index_col="adv_scopus")
    fields.index = fields.index.astype(str)
    adv_field = adv_field.join(fields).dropna().reset_index()
    advisers_by_field = adv_field.groupby("adv_jel")["adv_scopus"].unique()
    stu_field = stu_data[["stu_jel"]]
    students_by_field = (stu_field.reset_index()
                                  .groupby("stu_jel")["stu_id"].unique())
    print(">>> Distribution of no. of students and advisers per field:")
    counts = students_by_field.apply(len).to_frame("student")
    counts["adviser"] = advisers_by_field.apply(len)
    counts["ratio"] = counts["student"] / counts["adviser"]
    print(counts)

    # Randomize student-adviser assignment based on field (JEL code)
    stu_field = stu_field.join(advisers_by_field, on="stu_jel")
    stu_field = stu_field.dropna(subset=["adv_scopus"])
    n_max = []
    n_multiple = []
    print(f">>> Randomizing assignments 100 times...")
    for i in tqdm(range(0, 100)):
        stu_field["random"] = stu_field["adv_scopus"].apply(random.choice)
        stu_field[["random"]].to_csv(TARGET_FOLDER/f"random_field{i:03d}.csv")
        counts = stu_field["random"].value_counts()
        n_max.append(counts[0])
        n_multiple.append((counts > 1).sum())
    print(f"... found between {min(n_multiple)} and {max(n_multiple)} "
          "assignments whose adviser has more than 1 student")
    print(f"... most common adviser has between {min(n_max)} and {max(n_max)} "
          "students")


if __name__ == '__main__':
    main()
