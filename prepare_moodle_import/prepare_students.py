#! /usr/bin/env python

"""
Takes an essaim export of student information which must contain all columns 
seen in the transform function below.

Outputs a file ready for importing into Moodle : admin->users->import users
"""

import argparse
import sys

import pandas as pd

from lib import nth_or_none, prefix_year, prefixed_courses_list, read_excel, write_csv


def transform(src: pd.DataFrame) -> pd.DataFrame:
    if not src["adcMail"].is_unique:
        sys.exit("Found duplicate emails in file")

    res = pd.DataFrame()

    # We start with the columns that come from the source, thus creating all rows
    res["username"] = src["eleveUserName"]
    res["password"] = src["elevePassword"]
    res["firstname"] = src["welevePrenom"]
    res["lastname"] = src["weleveNom"]
    res["email"] = src["adcMail"]

    res["cohort1"] = prefix_year("eleves")
    res["cohort2"] = src["ElevesCursusActif::classe"].map(prefix_year)

    courses_list = src["ElevesCursusActif::xenclassDiscr"].map(prefixed_courses_list)
    max_number_of_courses = courses_list.map(len).max()
    if max_number_of_courses > 4:
        sys.exit(f"max number of courses is 4, we got {max_number_of_courses}")

    res["cohort3"] = courses_list.map(nth_or_none(0))
    res["cohort4"] = courses_list.map(nth_or_none(1))
    res["cohort5"] = courses_list.map(nth_or_none(2))
    res["cohort6"] = courses_list.map(nth_or_none(3))

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform an essaim student file into a csv for Moodle"
    )
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()

    df = read_excel(args.input)
    transformed = transform(df)
    write_csv(transformed, args.output)
