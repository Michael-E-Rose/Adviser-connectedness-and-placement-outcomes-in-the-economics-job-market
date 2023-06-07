#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Assembles centrality master files for regression."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from tqdm import tqdm

from _005_parse_students import write_stats

STUDENT_FILE = Path("./615_student_data/student.csv")
ADVISER_FILE = Path("./625_adviser_data/adviser.csv")
ADVSTU_FOLDER = Path("./199_adviser-student_map/")
TARGET_FOLDER = Path("./680_centrality_masters/")
OUTPUT_FOLDER = Path("./990_output/")

# Main placement rank/occurrence specification
COAUTH_SPEC = "plc_score-w"

mpl.use('Agg')
sns.set(style="whitegrid", font='Utopia')
plt.rc('axes', titlesize=20)


def count_adv_occurrences(df, score_var="plc_score-w", year_var='stu_year',
                          col='best_adviser', centr_var='first_ev-w-win99-std_mean'):
    """Count number of years in which adviser has placed students
    academically.
    """
    from collections import Counter
    mask = (~df[centr_var].isnull()) & (~df[score_var].isnull())
    subset = df.loc[mask, [col, year_var]]
    adv_count = Counter(subset.itertuples(index=False))
    adv_years = pd.DataFrame.from_dict(adv_count, orient='index')
    adv_years.index = pd.MultiIndex.from_tuples(list(adv_years.index))
    adv_years = adv_years.reset_index()
    counts = adv_years['level_0'].value_counts()
    return counts.to_frame(name="adv_occ")


def get_quartiles(temp, unit, var, verbose=False):
    """Safely compute non-overlapping sets compromising quartiles."""
    quartiles = temp[var].quantile([0.25, 0.5, 0.75]).values
    if verbose:
        print(f">>> Quartiles for {unit}: {quartiles}")
    q4_mask = temp[var] >= quartiles[2]
    q4_set = temp.loc[q4_mask, unit].value_counts()
    q3_mask = temp[var].between(quartiles[1], quartiles[2], "left")
    q3_set = temp.loc[q3_mask, unit].value_counts()
    q2_mask = temp[var].between(quartiles[0], quartiles[1], "left")
    q2_set = temp.loc[q2_mask, unit].value_counts()
    q1_mask = temp[var] < quartiles[0]
    q1_set = temp.loc[q1_mask, unit].value_counts()
    matrix = pd.concat([q4_set, q3_set, q2_set, q1_set], axis=1)
    matrix.columns = ["4", "3", "2", "1"]
    cats = matrix.idxmax(axis=1)
    cats.name = var + "_quartile"
    return cats


def make_histogramm(df, fname, var="plc_score-w-std", figsize=(10, 5),
                    label="Standarized placement score"):
    """Make histogramm with KDE overlay."""
    # Plot
    fig, ax1 = plt.subplots(figsize=figsize)
    sns.kdeplot(data=df, x=var, ax=ax1)
    ax2 = ax1.twinx()
    sns.histplot(data=df, x=var, discrete=True, ax=ax2)
    # Aesthetics
    for ax in [ax1, ax2]:
        ax.grid(False)
        ax.set_xlim((df[var].min()-1, df[var].max()+1))
        ax.set(xlabel=label)
    plt.tick_params(axis="both", which="major", length=5)
    sns.despine()
    # Save
    plt.savefig(fname, bbox_inches="tight")
    plt.close(fig)


def read_agg_centr(network):
    """Read aggregated centralities."""
    out = []
    for file in Path("./215_adviser_centralities/").glob(f"{network}*.csv"):
        new = pd.read_csv(file)
        new['year'] = int(file.stem[-4:])
        out.append(new)
    out = pd.concat(out)
    out["node"] = out["node"].astype("uint64")
    return (out.sort_values(["node", "year"])
               .set_index(["node", "year"]))


def read_distance_files():
    """Read all distance files and stack on top of each other."""
    dist = []
    files = sorted(Path("./217_placement_distance").glob("adviser_coauthor_*.csv"))
    cols = ["university", "adviser", "dist"]
    print(">>> Reading distance files:")
    for file in tqdm(files):
        new = pd.read_csv(file, index_col=['university', 'adviser'], usecols=cols)
        new = new.add_prefix("adv_")
        base, network, year = file.stem.split("_")
        new["year"] = int(year)
        dist.append(new)
    dist = pd.concat(dist).set_index("year", append=True)
    dist = dist[~dist["adv_dist"].isna()]
    return dist


def share_by_category(df, col='school_rank-w'):
    """Create DataFrame with numbers and shares of students by school group."""
    # Create rank category mapping
    rank_map = {float(r): 'Ranks 1-30' for r in range(1, 31)}
    rank_map.update({float(r): 'Ranks 31-100' for r in range(31, 101)})
    rank_map.update({float(r): 'Ranks 101-300' for r in range(101, 300)})
    # Aggregate counts
    counts = (df[col].map(rank_map).fillna('Other')
                .value_counts().to_frame('Initial'))
    counts['Share'] = round((counts['Initial'] / sum(counts['Initial']))*100, 1)
    return counts


def main():
    # Read student data
    df = pd.read_csv(STUDENT_FILE).drop(columns=["change_scopus"])
    print(f">>> Starting with {df.shape[0]:,} students")
    share_initial = share_by_category(df)
    df = df.drop(columns=["stu_scopus", "stu_rank"]).sort_values("stu_id")

    # Read auxiliary data
    adv_data = pd.read_csv(ADVISER_FILE, index_col=["adv_scopus", "year"])
    centr = read_agg_centr("coauthor")

    # Merge most prolific adviser and their data
    adv_actual = pd.read_csv(ADVSTU_FOLDER/"actual.csv", index_col="stu_id",
                             usecols=["stu_id", "adv_scopus"])
    df_a = df.join(adv_actual, on="stu_id")
    adv = (df_a.set_index(["stu_id", "stu_year"])['adv_scopus'].str.split(";", expand=True)
               .stack().to_frame("adviser")
               .droplevel(2).reset_index())
    adv["adviser"] = adv["adviser"].astype("uint64")
    best = adv.join(adv_data, on=['adviser', 'stu_year'])
    best = (best.sort_values('adv_euclid', ascending=False)
                .groupby('stu_id').head(1)  # Pick row with highest Euclid
                .rename(columns={'adviser': 'best_adviser'})
                .set_index('best_adviser'))
    df_a = (df_a.merge(best.reset_index(), how="inner", on=['stu_id', 'stu_year'])
                .drop(columns='adv_scopus'))
    df_a["best_adviser"] = df_a["best_adviser"].astype("uint64")
    print(f">>> {df_a.shape[0]:,} students left with adviser information")

    # Merge student data with random advisers
    print(">>> Creating files with random assignments")
    centr_cols = ["adv_ev-w-win99-std", "first_ev-w-win99-std_mean"]
    cols = ["plc_score-w-std", "adv_ev-w-win99-std", "first_ev-w-win99-std_mean",
            "adv_euclid", "adv_experience", "adviser", "stu_sex", "school_rank-w",
            "stu_year", "stu_jel", "stu_school", "adv_occ"]
    for r_file in tqdm(list(ADVSTU_FOLDER.glob("random*.csv"))):
        adv_random = pd.read_csv(r_file, index_col="stu_id")
        df_r = (df.join(adv_random, how="left", on="stu_id")
                  .rename(columns={"random": "adviser"})
                  .drop(columns='stu_plc'))
        df_r = df_r.join(adv_data, how="inner", on=['adviser', 'stu_year'])
        df_r["adviser"] = df_r["adviser"].astype("uint64")
        coauth_r = df_r.join(centr[centr_cols], on=['adviser', 'stu_year'])
        coauth_r = coauth_r.drop(columns=coauth_r.filter(like="plc_same", axis=1).columns)
        counts_r = count_adv_occurrences(coauth_r, col='adviser')
        coauth_r = coauth_r.join(counts_r, on="adviser")
        coauth_r.loc[coauth_r['adv_ev-w-win99-std'].isna(), "adv_occ"] = 0
        coauth_r["adv_occ"] = coauth_r["adv_occ"].fillna(0)
        coauth_r["adviser"] = "a" + coauth_r["adviser"].astype(str)
        coauth_r[cols].to_csv(TARGET_FOLDER/r_file.parts[-1], index=False)

    # Add social distance
    dist = read_distance_files()
    df_a = df_a.join(dist, on=["plc_scopus", "best_adviser", "stu_year"])

    # Compute lead adviser centralities
    centr = centr.reset_index()
    dummy = centr.copy()
    print(">>> Correlations between current and lead weighted EV centrality:")
    temp_drops = ['adv_deg', 'first_deg_mean', 'second_deg_mean', 'adv_ev-w_d',
                  'adv_ev-w-win99_d', 'adv_ev-w-std_d', 'adv_ev-w-win99-std_d',
                  'first_dec', 'second_dec', 'third_dec']
    for t in range(1, 3):
        lead = dummy.copy()
        lead["year"] -= t
        lead = lead.set_index(["node", "year"])
        suffix = f"_l{t}"
        centr = (centr.drop(columns=temp_drops)
                      .join(lead, on=["node", "year"], rsuffix=suffix))
        corr = centr[["adv_ev-w", "adv_ev-w" + suffix]].corr().iloc[0, 1]
        print(f"... with {t}-year lead: {corr:.3}")
    coauth = (df_a.merge(centr, left_on=['best_adviser', 'stu_year'],
                         right_on=["node", "year"], how="left")
                  .drop(columns=["year", "node"]))

    # Merge adviser occurrences
    coauth = coauth.join(count_adv_occurrences(coauth), on="best_adviser")
    coauth.loc[coauth['adv_ev-w'].isna(), "adv_occ"] = 0
    coauth["adv_occ"] = coauth["adv_occ"].fillna(0)

    # Add categories
    mask = ((coauth["adv_occ"] > 1) & (~coauth["plc_score-w-std"].isna())
            & (~coauth["adv_ev-w-win99-std"].isna()))
    temp = coauth[mask].copy()
    school_cats = get_quartiles(temp, unit="stu_school", var="school_rank-w", verbose=True)
    coauth = coauth.join(school_cats, on="stu_school")
    adv_euclid_cats = get_quartiles(temp, unit="best_adviser", var="adv_euclid")
    coauth = coauth.join(adv_euclid_cats, on="best_adviser")
    adv_exp_cats = get_quartiles(temp, unit="best_adviser", var="adv_experience")
    coauth = coauth.join(adv_exp_cats, on="best_adviser")

    # Write out actual advisers
    coauth["best_adviser"] = "a" + coauth["best_adviser"].astype(str)
    assert coauth.shape[0] == coauth["stu_id"].nunique()
    coauth.to_csv(TARGET_FOLDER/"master.csv", index=False)

    # Statistics
    ranked = ~coauth[COAUTH_SPEC].isnull()
    often = coauth["adv_occ"] >= 2
    final = coauth[often & ranked].copy()
    print(f">>> {final.shape[0]:,} observations in the coauthor sample")
    fname = OUTPUT_FOLDER/"Figures"/"placement_score_distribution.pdf"
    make_histogramm(final, fname)

    # Statistics
    network = ~coauth['adv_ev-w'].isnull()
    adviser = ~coauth['best_adviser'].isnull()
    often_no_plc = (network & often) & ~ranked
    stats = {'N_of_PhDs_with_adviser_no_centr': (~network & adviser).sum(),
             'N_of_Observations_coauth_centr': final.shape[0],
             'N_of_PhDs_with_adviser_often': often.sum(),
             'N_of_PhDs_with_adviser_not_often': (~often & adviser & network).sum(),
             'N_of_PhDs_with_adviser_with_placement_rank': (ranked & adviser).sum(),
             'N_of_PhDs_with_adviser_often_without_placement': often_no_plc.sum()}
    write_stats(stats)

    # Compute initial and final shares of students
    share_final = share_by_category(final)
    out = pd.concat([share_initial, share_final], axis=1)
    tuples = [('Initial', 'N'), ('Initial', 'Share'),
              ('Final', 'N'), ('Final', 'Share')]
    out.columns = pd.MultiIndex.from_tuples(tuples)
    sorting = {'Ranks 1-30': 0, 'Ranks 31-100': 1, 'Ranks 101-300': 2, 'Others': 3}
    out[('custom', "_")] = out.index.map(lambda i: sorting.get(i))
    out = out.sort_values(('custom', "_")).drop(columns=('custom', "_"))
    fname = OUTPUT_FOLDER/"Tables"/"centrality_distribution.tex"
    colfmt = "l*{2}{r@{\extracolsep{4mm}}}|*{2}{r@{\extracolsep{4mm}}}"
    out.to_latex(fname, multicolumn_format='c', column_format=colfmt)


if __name__ == '__main__':
    main()
