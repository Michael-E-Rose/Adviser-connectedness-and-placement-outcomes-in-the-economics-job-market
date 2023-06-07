#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Measures social and citation distance between all advisers and all
universities, before and after deceased faculty members are removed.
"""

from pathlib import Path

import pandas as pd
import pycountry
from numpy import where
from tqdm import tqdm
from pybliometrics.scopus import AffiliationRetrieval

from _005_parse_students import write_stats

tqdm.pandas()


INSTITUTION_FOLDER = Path("./090_institution_data/")
TARGET_FILE = Path("./117_faculty_lists/hasselback.csv")
FACULTY_FILE = 'https://raw.githubusercontent.com/Michael-E-Rose/Hasselback'\
               'FacultyRoster/master/hasselback.csv'


def create_country_map():
    """Create mapping of country names to alpha 2."""
    country_map = {}
    for country in pycountry.countries:
        country_map[country.name] = country.alpha_2
    country_map["Czech Republic"] = country_map["Czechia"]
    country_map["South Korea"] = country_map["Korea, Republic of"]
    country_map["Taiwan"] = country_map["Taiwan, Province of China"]
    country_map["Venezuela"] = country_map["Venezuela, Bolivarian Republic of"]
    country_map["Virgin Islands (U.S.)"] = country_map["United States"]
    return country_map


def flatten(lst):
    """Flatten two or more lists."""
    lst = lst.dropna()
    return set([e for sl in lst for e in sl if sl])


def get_aff_information(aff_id, refresh=False):
    """Get country and type of affiliation."""
    aff = AffiliationRetrieval(aff_id, refresh=refresh)
    country = country_map.get(aff.country)
    if not country:
        print(aff.country)
    return pd.Series({"country": country, "type": aff.org_type})


def interpolate_faculty(s):
    """Fill gaps of faculty membership."""
    # Add empty sets
    s = s.apply(lambda d: d or set())
    # Detect missing faculty and add in years between
    for idx0, last in list(s.items())[2:]:
        for idx1, current in list(s.items())[:-2]:
            try:
                new = last.intersection(current)
            except AttributeError:
                continue
            for idx2 in range(idx1+1, idx0):
                try:
                    s.loc[idx2].update(new)
                except KeyError:
                    continue
    return s


def setfy(x, sep=";"):
    """Split string into set."""
    return set(x.strip(sep).split(sep))


country_map = create_country_map()


def main():
    # Read Hasselback files
    df = pd.read_csv(FACULTY_FILE, dtype=str)
    df["scopus_id"] = df["scopus_id"] + ";"
    hass = pd.DataFrame()
    for c in sorted([c for c in df.columns if c.endswith("institution")]):
        year = c[1:5]
        subset = df[~df[c].isnull()].copy()
        group = subset.groupby([c])["scopus_id"].sum().to_frame()
        group["scopus_id"] = group["scopus_id"].str.rstrip(";").apply(setfy)
        group = group.rename(columns={"scopus_id": year})
        if year in hass.columns:
            group = pd.concat([hass[year], group], axis=1, sort=True)
            group = group.apply(flatten, axis=1).to_frame(name=year)
            hass = hass.drop(columns=year)
        hass = hass.join(group, how="outer")

    # Use integer column names
    rename = {y: int(y) for y in sorted(hass.columns)}
    hass = hass.rename(columns=rename)
    hass = hass[sorted(hass.columns)]

    # Interpolate faculty members
    for y in hass.columns:
        hass[y] = where(hass[y].isnull(), None, hass[y])
    hass = hass.apply(interpolate_faculty, axis=1)
    hass = hass[range(2000, 2005)]
    mask_empty = hass.applymap(len).sum(axis=1) == 0
    hass = hass[~mask_empty]
    years = hass.columns

    # Add Scopus information of institutions
    print(f">>> Adding affiliation information...")
    inst_map = pd.read_csv(INSTITUTION_FOLDER/"mapping.csv", index_col="our_name")
    hass = hass.join(inst_map)
    print("... institutions w/o Scopus ID:")
    print(hass[hass["Scopus"].isna()].index)
    hass = hass.dropna(subset="Scopus")
    hass["Scopus"] = hass["Scopus"].astype("uint64")
    info = hass["Scopus"].progress_apply(get_aff_information)
    hass = hass.join(info)

    # Applying corrections to Scopus' 'coll' classification
    coll_mask = hass.index.str.find("College") > -1
    hass.loc[coll_mask, "type"] = "coll"
    _univ = pd.read_csv(INSTITUTION_FOLDER/"univ.csv", header=None)[0].unique()
    univ_mask = hass.index.isin(_univ) | hass.index.str.startswith("CUNY")
    hass.loc[univ_mask, "type"] = "univ"
    hass = hass[hass["type"] == "univ"].drop(columns="type")

    # Maintenance
    print(">>> Distribution by country:")
    country_distribution = hass["country"].value_counts()
    print(country_distribution)

    # Count all faculty members
    hass = hass.set_index(["Scopus", "country"])
    all_members = set()
    for c in hass.columns:
        all_members.update({p for sl in hass[c].dropna().to_numpy() for p in sl})

    # Write out
    hass = hass.fillna("").applymap(lambda s: ";".join(sorted(s)))
    hass.to_csv(TARGET_FILE)
    stats = {"N_of_Hasselback_Dep": hass.shape[0],
             "N_of_Hasselback_Fac": len(all_members)}
    write_stats(stats)


if __name__ == '__main__':
    main()
