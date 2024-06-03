#! /usr/bin/env python

"""
Takes a file preprocessed by preprocess_teachers_and_courses.py

Outputs a file ready for importing into Moodle:
Admin->Cours->Modifier les cours en lots
"""

import argparse

import pandas as pd

from lib.io import read_csv, write_csv
from preprocess_teachers_and_courses import (
    COURSE_CATEGORY_PATH,
    COURSE_FULLNAME,
    COURSE_SHORTNAME,
)


def to_courses(src: pd.DataFrame) -> pd.DataFrame:
    res = src.copy()
    res = res[[COURSE_SHORTNAME, COURSE_FULLNAME, COURSE_CATEGORY_PATH]]
    res = res.sort_values(by=COURSE_SHORTNAME)
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("preprocessed")
    parser.add_argument("output")
    args = parser.parse_args()

    preprocessed = read_csv(args.preprocessed)
    courses = to_courses(preprocessed)
    write_csv(courses, args.output)
