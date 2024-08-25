#! /usr/bin/env python

"""
Takes a file preprocessed by preprocess_teachers_and_courses.py

Outputs a file ready for importing into Moodle:
Administration du site -> Plugins -> Inscriptions -> Upload enrolment methods
"""

import argparse

import polars as pl

from preprocess_teachers_and_courses import COURSE_COHORT, COURSE_SHORTNAME


def to_enrollment_methods(src: pl.DataFrame) -> pl.DataFrame:
    src = src.drop_nulls(COURSE_COHORT)

    res = pl.DataFrame().with_columns(
        src[COURSE_COHORT].alias("metacohort"),
        src[COURSE_SHORTNAME].alias("shortname"),
        pl.lit("add").alias("operation"),
        pl.lit("cohort").alias("method"),
        pl.lit(0).alias("disabled"),
        pl.lit("student").alias("role"),
    )
    res = res.sort(by="shortname")
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("preprocessed")
    parser.add_argument("output")
    args = parser.parse_args()

    preprocessed = pl.read_csv(args.preprocessed)
    enrollment_methods = to_enrollment_methods(preprocessed)
    enrollment_methods.write_csv(args.output)
