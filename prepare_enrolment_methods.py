#! /usr/bin/env python

"""
Takes a file preprocessed by preprocess_teachers_and_courses.py

Outputs a file ready for importing into Moodle:
Administration du site -> Plugins -> Inscriptions -> Upload enrolment methods
"""

import argparse

import pandas as pd

from lib.io import read_csv, write_csv
from preprocess_teachers_and_courses import COURSE_COHORT, COURSE_SHORTNAME


def to_enrollment_methods(src: pd.DataFrame) -> pd.DataFrame:
    res = pd.DataFrame()

    # We start with the columns that come from the source, thus creating all rows
    res["metacohort"] = src[COURSE_COHORT]
    res["shortname"] = src[COURSE_SHORTNAME]

    # Now we can set the constant values to the rest of the columns
    res["operation"] = "add"
    res["method"] = "cohort"
    res["disabled"] = 0
    res["role"] = "student"

    # To help compare different runs of the tool
    res.sort_values(by="shortname", inplace=True)

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("preprocessed")
    parser.add_argument("output")
    args = parser.parse_args()

    preprocessed = read_csv(args.preprocessed)
    enrollment_methods = to_enrollment_methods(preprocessed)
    write_csv(enrollment_methods, args.output)
