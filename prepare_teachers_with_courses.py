"""
Takes a file preprocessed by preprocess_teachers_and_courses.py

Outputs a file containing teacher information and their courses,
ready for importing into Moodle : Admin->Utilisateurs->Importation d'utilisateurs
"""

import argparse
import os
import sys
from typing import Callable

import dotenv
import polars as pl

from lib.passwords import password_generator
from preprocess_teachers_and_courses import (
    COURSE_SHORTNAME,
    TEACHER_EMAIL,
    TEACHER_FIRSTNAME,
    TEACHER_LASTNAME,
    TEACHER_TLA,
)


def make_names(name: str, count: int):
    return [f"{name}{i + 1}" for i in range(count)]


def to_teachers_with_courses(
    src: pl.DataFrame, email_to_password: Callable[[str], str]
) -> pl.DataFrame:
    res = src.group_by(TEACHER_TLA).agg(
        pl.min(TEACHER_LASTNAME),
        pl.min(TEACHER_FIRSTNAME),
        pl.min(TEACHER_EMAIL),
        pl.col(COURSE_SHORTNAME),
    )

    course_count = res.select(pl.col(COURSE_SHORTNAME).list.len()).max().item()

    # Dynamically build the course columns based on the list we collected in the shortname column
    res = res.with_columns(
        pl.col(COURSE_SHORTNAME).list.to_struct(
            fields=make_names("course", course_count)
        )
    ).unnest(COURSE_SHORTNAME)

    # Type 2 to make users teachers for their courses
    type_columns = {name: pl.lit(2) for name in make_names("type", course_count)}
    res = res.with_columns(**type_columns)

    ######
    # Generate all required columns
    ######
    res = res.with_columns(
        cohort1=pl.lit(1),  #  Enseignants au gymnase de Beaulieu
        username=pl.col(TEACHER_EMAIL),
        password=pl.col(TEACHER_EMAIL).map_elements(
            email_to_password, return_dtype=pl.String
        ),
    )

    #####
    # Make the resulting columns look as expected
    ######
    res = res.rename(
        {
            TEACHER_LASTNAME: "lastname",
            TEACHER_FIRSTNAME: "firstname",
            TEACHER_EMAIL: "email",
        }
    )

    res = res.drop(TEACHER_TLA)

    # For human readability
    res = res.sort(["lastname", "firstname"])

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("preprocessed")
    parser.add_argument("output")
    args = parser.parse_args()

    dotenv.load_dotenv()
    salt = os.getenv("SALT")
    if not salt:
        sys.exit("Missing environment variable 'SALT'")

    preprocessed = pl.read_csv(args.preprocessed)
    teachers_with_courses = to_teachers_with_courses(
        preprocessed, password_generator(salt)
    )
    teachers_with_courses.write_csv(args.output)
