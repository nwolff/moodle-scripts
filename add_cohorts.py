"""
Takes a file preprocessed by preprocess_teachers_and_courses.py

Uses the Moodle API to create all the cohorts in the file.

Parameter course_category_id is the id number of the yearly category.
It can be found here:
https://moodle.gymnasedebeaulieu.ch/course/management.php


This script replaces an older script that generated a file that could be imported with
Administration du site -> Utilisateur -> Cohortes -> Déposer les cohortes.
That technique prevented us from synchronizing cohorts more than once, because that
admin page choked as soon as a cohort in the file already existed in Moodle.
"""

import argparse
import os
import sys

import dotenv
import polars as pl
import structlog

from lib.moodle_api import URL, MoodleClient
from preprocess_teachers_and_courses import COURSE_COHORT

log = structlog.get_logger()


def add_cohorts(moodle: MoodleClient, course_category_id: str, src: pl.DataFrame):
    wanted = set(src[COURSE_COHORT].drop_nulls())
    log.info("wanted cohorts", count=len(wanted))

    result = moodle(
        "core_cohort_search_cohorts",
        query="",
        context={"contextlevel": "coursecat", "instanceid": course_category_id},
        includes="self",
        limitfrom=0,
        limitnum=10000,
    )
    existing = {c.name for c in result.cohorts}
    log.info(
        "fetched existing from moodle",
        course_category_id=course_category_id,
        found=len(existing),
    )

    # We just display these, in case the user wants to remove them
    extra = sorted(existing - wanted)
    log.info("extra cohorts", extra=extra)

    missing = sorted(wanted - existing)
    log.info("missing cohorts", missing=missing)

    if not missing:
        log.info("no missing cohorts, nothing to do.")
        sys.exit(0)

    user_input = input(f"Do you want to create {len(missing)} cohorts (yes/no): ")
    if user_input.lower() != "yes":
        print("aborting")
        sys.exit(0)

    data = [
        dict(categorytype=dict(type="id", value=course_category_id), name=c, idnumber=c)
        for c in missing
    ]

    moodle("core_cohort_create_cohorts", cohorts=data)
    log.info("done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("course_category_id")
    parser.add_argument("preprocessed")
    args = parser.parse_args()

    dotenv.load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        sys.exit("Missing environment variable 'TOKEN'")

    log.info("connecting", url=URL, token=token)
    moodle = MoodleClient(URL, token)

    preprocessed = pl.read_csv(args.preprocessed)
    add_cohorts(moodle, args.course_category_id, preprocessed)
