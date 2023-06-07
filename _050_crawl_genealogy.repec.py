#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Crawls genealogy.repec.org for adviser information."""

from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

SOURCE_FILE = Path('./005_student_lists/main.csv')
TARGET_FILE = Path('./050_adviser_genealogy.repec/repec.csv')


def crawl(handle):
    """Attempt to extract supervisor information from genealogy.repec.org."""
    url = 'https://genealogy.repec.org/pages/' + handle + '.html'
    r = requests.get(url)
    advisers = [("-", "-")]
    if r.status_code < 400:
        soup = BeautifulSoup(r.text, 'lxml')
        adv_tags = soup.find('ol')
        advisers = []
        for adv_tag in adv_tags.findAll('li'):
            advisers.append(get_names_and_links(adv_tag))
    adv_names = "; ".join(x[0] for x in advisers)
    adv_urls = "; ".join(x[1] for x in advisers)
    return pd.Series({'adviser_name': adv_names, 'adviser_url': adv_urls})


def get_names_and_links(tag):
    """Return tuple of adviser and link to repec profile if present."""
    name = tag.text.split('(')[0].strip()
    if name == "No advisor listed, help complete this page.":
        name = "-"
    try:
        url = tag.findAll('a')[-1]['href']
    except IndexError:
        url = "-"
    return name, url


def main():
    cols = ['stu_id', 'stu_repec']
    stu_df = pd.read_csv(SOURCE_FILE, index_col='stu_id', usecols=cols).dropna()

    adv_df = stu_df['stu_repec'].apply(crawl)
    adv_df['adviser_name'] = adv_df['adviser_name'].str.replace('  ', ' ')
    adv_df = adv_df.replace("-", "").replace("-; -", "")

    adv_df.sort_index().to_csv(TARGET_FILE, index_label="stu_id")


if __name__ == '__main__':
    main()
