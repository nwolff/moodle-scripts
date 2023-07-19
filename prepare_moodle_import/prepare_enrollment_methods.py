#! /usr/bin/env python

"""
Takes an essaim export as input, the file must contain two columns:
shortname and cohort1

Outputs a file ready for importing into Moodle: 
Administration du site -> Plugins -> Inscriptions -> Upload enrolment methods
"""

import argparse

import pandas as pd

from lib import read_csv, write_csv


def transform(src: pd.DataFrame) -> pd.DataFrame:
    res = pd.DataFrame()

    # We start with the columns that come from the source, thus creating all rows
    res["shortname"] = src["shortname"]
    res["metacohort"] = src["cohort1"]

    # Now we can set the constant values to the rest of the columns
    res.insert(0, "operation", "add")
    res.insert(1, "method", "cohort")
    res["disabled"] = 0
    res["role"] = "student"
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
