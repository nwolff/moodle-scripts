"""
Takes a file preprocessed by preprocess_teachers_and_courses.py

Outputs a file ready for importing into Moodle:
Admin->Cours->Modifier les cours en lots
"""

import argparse

import polars as pl
import structlog

from preprocess_teachers_and_courses import (
    COURSE_CATEGORY_PATH,
    COURSE_FULLNAME,
    COURSE_SHORTNAME,
)

log = structlog.get_logger()


def to_courses(src: pl.DataFrame) -> pl.DataFrame:
    res = src.select([COURSE_SHORTNAME, COURSE_FULLNAME, COURSE_CATEGORY_PATH])
    res = res.sort(by=COURSE_SHORTNAME)
    log.info(
        "done",
        num_courses=len(res),
    )
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("preprocessed")
    parser.add_argument("output")
    args = parser.parse_args()

    preprocessed = pl.read_csv(args.preprocessed)
    courses = to_courses(preprocessed)
    courses.write_csv(args.output)
