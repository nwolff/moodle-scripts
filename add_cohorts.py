#! /usr/bin/env python

"""
Takes a file preprocessed by preprocess_teachers_and_courses.py

Uses the Moodle API to create all the cohorts in the file.

Parameter course_category_id is the id number of the yearly category.
It can be found here:
https://moodle.gymnasedebeaulieu.ch/course/management.php


This script replaces an older script that generated a file that could be imported with
Administration du site -> Utilisateur -> Cohortes -> Déposer les cohortes
because that admin page choked as soon as a cohort in the file already exists
"""

import argparse
import os
import sys

import dotenv
import pandas as pd
import structlog

from lib.io import read_csv
from lib.moodle_api import URL, MoodleClient
from preprocess_teachers_and_courses import COURSE_COHORT

log = structlog.get_logger()


def add_cohorts(moodle: MoodleClient, course_category_id: str, src: pd.DataFrame):
    wanted = set(src[COURSE_COHORT])
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
        "fetched cohorts from moodle",
        course_category_id=course_category_id,
        count=len(existing),
    )

    missing = wanted - existing
    if not missing:
        log.info("Nothing to do")
        sys.exit(0)

    log.info("Missing cohorts", missing=missing)

    user_input = input(f"Do you want to create {len(missing)} cohorts (yes/no): ")
    if user_input.lower() != "yes":
        print("Aborting")
        sys.exit(0)

    data = [
        dict(categorytype=dict(type="id", value=course_category_id), name=c, idnumber=c)
        for c in missing
    ]

    moodle("core_cohort_create_cohorts", cohorts=data)
    log.info("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("course_category_id")
    parser.add_argument("preprocessed")
    args = parser.parse_args()

    dotenv.load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        sys.exit("Missing environment variable 'TOKEN'")

    log.info("connecting", url=URL)
    moodle = MoodleClient(URL, token)

    preprocessed = read_csv(args.preprocessed)
    add_cohorts(moodle, args.course_category_id, preprocessed)
