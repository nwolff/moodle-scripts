#! /usr/bin/env python

"""
Takes a file preprocessed by preprocess_teachers_and_courses.py

Outputs a file containing teacher information and their courses,
ready for importing into Moodle : Admin->Utilisateurs->Importation d'utilisateurs
"""

import argparse
from itertools import zip_longest

import pandas as pd

from lib.io import read_csv, write_csv
from lib.passwords import random_moodle_password
from preprocess_teachers_and_courses import (
    COURSE_SHORTNAME,
    TEACHER_EMAIL,
    TEACHER_FIRSTNAME,
    TEACHER_LASTNAME,
    TEACHER_PEDAGO_LOGIN,
    TEACHER_TLA,
)


def make_names(name: str, count: int = 100):
    return [f"{name}{i}" for i in range(1, count + 1)]


def to_teachers_with_courses(src: pd.DataFrame) -> pd.DataFrame:
    res = src.copy()
    res = res.groupby(TEACHER_TLA).agg(
        {
            TEACHER_LASTNAME: pd.Series.min,
            TEACHER_FIRSTNAME: pd.Series.min,
            TEACHER_EMAIL: pd.Series.min,
            TEACHER_PEDAGO_LOGIN: pd.Series.min,
            COURSE_SHORTNAME: pd.Series.tolist,
        }
    )

    # Dynamically build the course columns based on the list we collected in the shortname column
    # https://stackoverflow.com/questions/75565785/pandas-list-unpacking-to-multiple-columns
    courses_column_names = make_names("course")
    # Important to make courses a list, otherwise it gets spent the first time we iterate it
    courses = list(zip_longest(*res[COURSE_SHORTNAME]))
    d = dict(zip(courses_column_names, courses))
    res = res.assign(**d)

    # Type 2 to make users teachers for their courses
    for i in range(len(list(courses))):
        res[f"type{i+1}"] = 2

    ###
    # Final formatting
    ###
    res = res.drop(columns=[COURSE_SHORTNAME])

    res["cohort1"] = 1  #  Enseignants au gymnase de Beaulieu

    # XXX: Sometimes is this, sometimes is that
    # res["username"] = res[TEACHER_EMAIL]
    res["username"] = res[TEACHER_PEDAGO_LOGIN]

    res = res.drop(columns=[TEACHER_PEDAGO_LOGIN])

    res = res.sort_values([TEACHER_LASTNAME, TEACHER_FIRSTNAME])

    res["password"] = [random_moodle_password() for _ in range(len(res))]

    res = res.rename(
        columns={
            TEACHER_LASTNAME: "lastname",
            TEACHER_FIRSTNAME: "firstname",
            TEACHER_EMAIL: "email",
        }
    )

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("preprocessed")
    parser.add_argument("output")
    args = parser.parse_args()

    preprocessed = read_csv(args.preprocessed)
    teachers_with_courses = to_teachers_with_courses(preprocessed)
    write_csv(teachers_with_courses, args.output)
