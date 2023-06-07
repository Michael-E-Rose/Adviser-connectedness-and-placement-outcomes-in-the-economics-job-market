#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Compiles all available data on students and adds the following:
1. Placement type
2. Placement retainment
3. Citation count immediately after placement
4. Rank and year of first affiliaton change
"""

from collections import defaultdict
from pathlib import Path

import pandas as pd
from pybliometrics.scopus import CitationOverview, ScopusSearch
from tqdm import tqdm

from _005_parse_students import write_stats
from _117_get_faculty_lists import create_country_map
from _215_compute_adviser_centralities import standardize, winsorize
from _401_rank_institutions import END_YEAR

STUDENT_FILE = Path("./005_student_lists/main.csv")
PLACEMENT_FILE = Path("./020_placements/placements.csv")
MAPPING_FOLDER = Path("./090_institution_data/")
ADVISER_MAP = Path("./199_adviser-student_map/actual.csv")
GENDER_FILE = Path("./608_gender_estimates/genderize.csv")
TARGET_FILE = Path("./615_student_data/student.csv")

CITATION_RANGE = 5  # Count cites to publications this many years past placement
PLATFORMS = {"60020337", "60016621", "60007893"}

_aff_map = pd.read_csv(MAPPING_FOLDER/"non_org.csv", dtype=str).set_index("nonorg")["org"].to_dict()
tqdm.pandas()


def compare_placement(aff_d, placement):
    """Compare whether the placement is in the set of affiliations,
    considering a certain lag.
    """
    same = {}
    old_aff = True
    for lag, affs in aff_d.items():
        if lag > 9:
            continue
        key = f"plc_same-{lag:02d}"
        if affs:
            value = placement in affs
            old_aff = placement in affs
        else:
            value = old_aff
        same[key] = int(value)
    return same


def find_affiliation(p, auth_id):
    """Find affiliation in an author's publication."""
    try:
        idx = p.author_ids.index(str(int(auth_id)))
        affs = p.author_afids.split(";")[idx] or None
        affs = set(affs.split("-"))
        affs = set(_aff_map.get(a, a) for a in affs) - PLATFORMS
        return affs
    except (AttributeError, ValueError):  # No affiliation or author not in list
        return set()


def get_affiliation_type(aff_id, refresh=100):
    """Get type of placement according to Scopus."""
    from pybliometrics.scopus import AffiliationRetrieval
    try:
        aff_id = int(aff_id)
        aff = AffiliationRetrieval(aff_id, refresh=refresh)
        org_type = aff.org_type
        country = country_map.get(aff.country)
        if aff.country and not country:
            print(aff.country)
    except ValueError:
        org_type = None
        country = None
    return pd.Series({"plc_type": org_type, "plc_country": country})


def parse_affiliations(df, scopus_id, base_year):
    """Parse affiliations listed on papers and sort them
    relative to `base_year`.
    """
    # Get affiliations from papers
    max_year = df["year"].max()
    affs = defaultdict(lambda: set())
    temp = df.dropna(subset=["author_afids"]).copy()
    temp["lag"] = temp["year"] - base_year
    temp = temp[temp["lag"] > 0]  # Consider only papers past PhD
    if temp.empty:
        return affs
    temp["aff"] = temp.apply(lambda s: find_affiliation(s, scopus_id), axis=1)
    # Fill active years w/o publication
    for y in range(1, max_year-base_year):
        affs[y].update(set())
    # Record all affiliations
    for _, p in temp.iterrows():
        affs[p.lag].update(p.aff)
    return affs


def query_publications(scopus_id, refresh=100):
    """Retrieve publications for a student."""
    res = ScopusSearch(f"AU-ID({scopus_id})", refresh=refresh).results
    cols = ["coverDate", "author_ids", "author_afids"]
    temp = pd.DataFrame(res).set_index("eid")[cols]
    temp["year"] = temp["coverDate"].str[:4].astype("int32")
    return temp[temp["year"] <= END_YEAR].sort_values("year")


def read_rankings(verbose=True):
    """Read our version of the unweighted and SJR weighted Tilburg
    Economics Ranking.
    """
    # Read in
    folder = Path("./401_institution_rankings/")
    weighted = pd.read_csv(folder/"weighted.csv", encoding="utf",
                           index_col=["institution", "year"])
    weighted = weighted.add_suffix("-w").reset_index()
    if verbose:
        sd = weighted.loc[weighted["year"] == 2004, "score-w"].std()
        print(f">>> 1 SD in the weighted score in 2004 equals {sd:.2f}")
    weighted = standardize_winsorize_df(weighted, col="score-w")
    unweighted = pd.read_csv(folder/"unweighted.csv", encoding="utf")
    unweighted = standardize_winsorize_df(unweighted)
    # Combine
    return weighted.join(unweighted, how="outer")


def retrieve_citations(df, year, refresh=False):
    """Compute total citation count for the first `CITATION_RANGE` years
    past graduation.
    """
    # Retrieve citation count until `year` + `CITATION_RANGE`
    cit_year = year + CITATION_RANGE
    eids = df[df["year"] <= cit_year].index.to_list()
    min_year = df["year"].min()
    doc_ids = [eid.split("-")[-1] for eid in eids]
    if not doc_ids:
        cites = None
    else:
        sub_lists = [doc_ids[i:i + 25] for i in range(0, len(doc_ids), 25)]
        cites = 0
        for sub_list in sub_lists:
            co = CitationOverview(sub_list, start=min_year, refresh=refresh)
            for p in co.cc:
                cites += sum([t[1] for t in p if t[0] < cit_year])
    return cites


def standardize_winsorize_df(df, col="score"):
    """Standardize and winsorize a column in a DataFrame year-wise."""
    df[f"{col}-std"] = df.groupby("year")[col].apply(standardize)
    grouped = df.groupby("year")
    df[f"{col}-win"] = grouped[col].apply(winsorize)
    df[f"{col}-std-win"] = grouped[f"{col}-std"].apply(winsorize)
    return df.set_index(["institution", "year"])


country_map = create_country_map()


def main():
    # Read in
    cols = ['stu_id', 'stu_school', 'stu_jel', 'stu_year', 'stu_scopus']
    students = pd.read_csv(STUDENT_FILE, index_col="stu_id", usecols=cols)
    plc = pd.read_csv(PLACEMENT_FILE, encoding="utf8").drop(columns="source")
    df = plc.join(students, how="inner", on="stu_id")

    # Store students w/o placement
    no_placement = set(students.index) - set(df["stu_id"].unique())
    no_placement = pd.DataFrame(index=sorted(no_placement))
    print(f">>> No placement information for {no_placement.shape[0]:,} students")
    stats = {'N_of_PhDs_without_placement': no_placement.shape[0]}

    # Drop students w/o placement year
    mask = df['plc_year'].isna()
    print(f">>> No placement year for {mask.sum():,} students")
    df.loc[mask, 'stu_plc'] = None

    # Ignore placements past two years after PhD
    mask = df["plc_year"] > df["stu_year"] + 2
    df.loc[mask, ["stu_plc", "stu_rank"]] = None
    df = df[['stu_id', 'stu_plc', 'stu_rank', 'plc_year', 'stu_year']]

    # Add Scopus IDs of placements
    affmap = pd.read_csv(MAPPING_FOLDER/"mapping.csv", index_col="our_name")
    df = (df.join(affmap, on="stu_plc")
            .rename(columns={"Scopus": "plc_scopus"}))

    # Add rankings of placements
    ranks = read_rankings()
    df = (df.join(ranks.add_prefix("plc_"), on=["plc_scopus", "stu_year"])
            .set_index("stu_id")
            .drop(columns="stu_year"))
    df = students.join(df).sort_index()
    mask_ranked = ~df['plc_rank-w'].isna()
    print(f">>> {df['stu_plc'].nunique():,} ranked placements "
          f"for {mask_ranked.sum():,} students")
    stats['N_of_PhDs_with_ranked_placement'] = mask_ranked.sum()

    # Store unranked placements
    no_rank = df[~mask_ranked].dropna(subset=["plc_year"]).copy()
    no_rank = no_rank["plc_scopus"].fillna(no_rank["stu_plc"]).dropna()
    stats['N_of_PhDs_without_ranked_placement'] = no_rank.shape[0]
    no_rank = (no_rank.astype("str").str.replace(".0", "", regex=False)
                      .value_counts().to_frame('Occurrences'))
    no_rank.index.name = "Affiliation"
    no_rank = (no_rank.reset_index()
                      .sort_values(["Occurrences", "Affiliation"],
                                   ascending=[False, True]))
    print(f">>> {no_rank.shape[0]} unranked placements for "
          f"{sum(no_rank['Occurrences']):,} students")

    # Merge affiliation types
    print(f">>> Retrieving affiliation information...")
    info = df['plc_scopus'].progress_apply(get_affiliation_type)
    df = pd.concat([df, info], axis=1)
    print("... Distribution of types and countries:")
    print(df['plc_type'].value_counts())
    print(df['plc_country'].value_counts())

    # Merge with gender information (assume unknowns to be male)
    gender = pd.read_csv(GENDER_FILE, index_col="id", usecols=["id", "gender"])
    gender = gender.rename(columns={"gender": "stu_sex"}).fillna("male")
    gender.index.name = "stu_id"
    df = df.join(gender)

    # Merge with school ranks
    df = (df.join(affmap.dropna(), on='stu_school')
            .join(ranks.add_prefix("school_"), on=('Scopus', 'stu_year'))
            .rename(columns={'Scopus': 'school_scopus'}))
    assert(df['school_rank-w'].isna().sum() == 0)

    # Drop students w/o Scopus ID
    no_scopus = df[df["stu_scopus"].isna()].reset_index()[["stu_id"]]
    print(f">>> Found {no_scopus.shape[0]} ({no_scopus.shape[0]/df.shape[0]:.2%}) "
          "students w/o Scopus profile")

    # Retrieve career and citation information
    print(">>> Counting citations and searching affiliations...")
    affs = {}
    cites = {}
    change = {}
    coauthors = {}
    students = students.dropna(subset=["stu_scopus"])
    advisers = pd.read_csv(ADVISER_MAP, index_col="stu_id",
                           usecols=["stu_id", "adv_scopus"])
    advisers["adv_scopus"] = advisers["adv_scopus"].str.split(";")
    students = students.join(advisers)
    students = students.dropna(subset=["adv_scopus"])
    adv_map = students["adv_scopus"].to_dict()
    for idx, row in tqdm(df.iterrows(), total=df.shape[0]):
        # Query publications
        try:
            student_id = int(row["stu_scopus"])
        except ValueError:
            continue
        pubs = query_publications(student_id)
        # Retrieve co-authors
        stu_adv = set(adv_map.get(idx, set()))
        pubs["author_ids"] = pubs["author_ids"].str.split(";")
        mask_five = pubs["year"].between(row.stu_year, row.stu_year+5)
        coauth = pubs[mask_five]["author_ids"]
        coauthors[student_id] = set([a for sl in coauth for a in sl])
        # Retrieve citations
        mask_with_adv = pubs["author_ids"].apply(
            lambda s: len(stu_adv.intersection(s)) > 0)
        try:
            cites[student_id] = retrieve_citations(pubs[~mask_with_adv], row["stu_year"])
        except KeyError:
            pass
        # Retrieve affiliations
        if row["plc_scopus"] != row["plc_scopus"]:
            continue
        aff_d = parse_affiliations(pubs, str(student_id), int(row["plc_year"]))
        retention = compare_placement(aff_d, str(int(row["plc_scopus"])))
        affs[student_id] = retention
        # Get first affiliation after change
        try:
            idx = min([k for k, v in retention.items() if v == 0])
            lag = int(idx.split("-")[-1])
            change[student_id] = (aff_d[lag], row["plc_year"]+lag)
        except ValueError:
            change[student_id] = (None, None)
    change = pd.Series(change).apply(pd.Series).dropna()
    change.columns = ["aff_id", "change_year"]
    change = change.explode('aff_id')
    change["aff_id"] = change["aff_id"].astype("uint64")

    # Compute affiliation rank of changes
    change = change.join(ranks[["rank-w", "rank"]].add_prefix("change_"),
                         on=('aff_id', 'change_year'))
    change.index.name = "stu_scopus"
    change = change.sort_values(["change_rank-w", "aff_id"])
    change = change[~change.index.duplicated(keep='first')]
    change = (change.reset_index().rename(columns={"aff_id": "change_scopus"})
                    .sort_values("change_rank-w")
                    .drop_duplicates(subset=["stu_scopus"])
                    .set_index("stu_scopus"))

    # Merge all
    cite_label = f"stu_citestock_{CITATION_RANGE}p"
    df = (df.join(pd.DataFrame(affs).T, on='stu_scopus')
            .drop("school_scopus", axis=1)
            .join(pd.Series(cites, name=cite_label), on="stu_scopus")
            .join(change, on="stu_scopus"))

    # Write out
    df.to_csv(TARGET_FILE, index_label="stu_id")
    write_stats(stats)

    # Maintenance
    no_pubs = df[df[cite_label].isna()]["stu_scopus"].dropna().astype("uint64")
    print(f">>> Found {no_pubs.shape[0]} students w/ Scopus profile ID but "
          f"w/o publications {CITATION_RANGE} years past graduation")

    # Compare with advisors
    coauthors = pd.Series(coauthors)
    students = students.dropna(subset="adv_scopus").set_index("stu_scopus")
    students["coauthors"] = coauthors
    students["joint_pub"] = students.apply(
        lambda s: len(s["coauthors"].intersection(s["adv_scopus"])), axis=1)
    joint_pub = students['joint_pub'].sum()
    print(f">>> {joint_pub:,} students publish with their adviser(s) within "
          f"5 years past graduation {joint_pub/students.shape[0]:.1%}")


if __name__ == '__main__':
    main()
