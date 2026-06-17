"""
Takes:
- a top-level category id
- a file preprocessed by preprocess_teachers_and_courses.py

compares the list of courses found in moodle vs the list of courses in the file

Uses the Moodle API
"""

import argparse

import polars as pl
import structlog

from lib.config import get_moodle_client
from lib.moodle_api import MoodleClient
from preprocess_teachers_and_courses import COURSE_SHORTNAME

log = structlog.get_logger()


def diff_courses(moodle: MoodleClient, course_category_id: str, src: pl.DataFrame):
    categories = moodle(
        "core_course_get_categories",
        criteria=[{"key": "id", "value": course_category_id}],
    )
    categories.sort(key=lambda x: x.id)

    existing_courses = []
    for category in categories:
        log.debug(
            "collecting courses",
            category=category.name,
            course_count=category.coursecount,
        )
        courses_in_category = moodle(
            "core_course_get_courses_by_field", field="category", value=category.id
        )
        existing_courses.extend(courses_in_category.courses)

    wanted = set(src[COURSE_SHORTNAME])
    existing = {c.shortname for c in existing_courses}

    # We just display these, in case the user wants to remove them
    extra = sorted(existing - wanted)
    log.info("in moodle but not in file", courses=extra)

    missing = sorted(wanted - existing)
    log.info("in file but not in moodle", courses=missing)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("course_category_id")
    parser.add_argument("preprocessed")

    args = parser.parse_args()

    preprocessed = pl.read_csv(args.preprocessed)

    moodle = get_moodle_client()
    diff_courses(moodle, args.course_category_id, preprocessed)
