#! /usr/bin/env python

"""
Takes an essaim export as input with column cohort1

Outputs a file ready for importing into Moodle: 
Administration du site -> Utilisateur -> Cohortes -> Déposer les cohortes 
"""

import argparse

import pandas as pd

from lib import read_csv, write_csv


def transform(src: pd.DataFrame) -> pd.DataFrame:
    res = pd.DataFrame()
    uniqueSortedCohorts = src["cohort1"].sort_values().unique()
    res["name"] = uniqueSortedCohorts
    res["idnumber"] = uniqueSortedCohorts
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform an essaim course and cohort file into a csv for Moodle"
    )
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()

    # The separator is hardcoded. The pandas doc say we could use None,
    # but that triggers a bug where we later cannot retrieve the first column.
    df = read_csv(args.input, sep=";")
    transformed = transform(df)
    write_csv(transformed, args.output)
