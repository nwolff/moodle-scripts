"""
Takes a file preprocessed by preprocess_teachers_and_courses.py

Outputs a file ready for importing into Moodle:
Administration du site -> Plugins -> Inscriptions -> Upload enrolment methods
"""

import argparse

import polars as pl
import structlog

from preprocess_teachers_and_courses import COURSE_COHORT, COURSE_SHORTNAME

log = structlog.get_logger()


def to_enrollment_methods(src: pl.DataFrame) -> pl.DataFrame:
    src = src.drop_nulls(COURSE_COHORT)

    res = (
        pl.DataFrame()
        .with_columns(
            metacohort=src[COURSE_COHORT],
            shortname=src[COURSE_SHORTNAME],
            operation=pl.lit("add"),
            method=pl.lit("cohort"),
            disabled=pl.lit(0),
            role=pl.lit("student"),
        )
        .sort(by="shortname")
    )

    log.info(
        "done",
        num_enrollment_methods=len(res),
    )

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("preprocessed")
    parser.add_argument("output")
    args = parser.parse_args()

    preprocessed = pl.read_csv(args.preprocessed)
    enrollment_methods = to_enrollment_methods(preprocessed)
    enrollment_methods.write_csv(args.output)
