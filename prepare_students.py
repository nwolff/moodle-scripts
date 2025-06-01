#! /usr/bin/env python

"""
Takes an essaim export of students that looks like this:

adcMail                 weleveNomUsuel      welevePrenomUsuel       ElevesCursusActif::classe  ElevesCursusActif::xenclassDiscr
h.muster@eduvaud.ch     MUSTER              Hans                    3M05                       3MAL4 - An - NR - 3MOSPM2 - 3MOCMU1 - TM
j.ballard@eduvaud.ch    BALLARD             Justine                 3CCI1                      3CAL3 - 3CALOCI1 - CI

Outputs a file ready for importing into Moodle : admin->users->import users

Uses the Moodle API to retrieve the list of existing cohorts and filters courses that don't have a matching cohort.
This implies YOU MUST ADD COHORTS BEFORE RUNNING THIS SCRIPT.
"""

import argparse
import os
import sys
from typing import Callable

import dotenv
import pandas as pd
import structlog

from lib.io import read_excel, write_csv
from lib.moodle_api import URL, MoodleClient
from lib.passwords import password_generator
from lib.schoolyear import END_YY, START_YY

log = structlog.get_logger()

YEAR_PREFIX = f"{START_YY}{END_YY}_"


def transform(
    src: pd.DataFrame, email_to_password: Callable[[str], str], moodle: MoodleClient
) -> pd.DataFrame:
    log.info("start", student_count=len(src))

    # Some students don't have an email address (yet),
    # so we can't create their moodle account
    students_with_no_email = src["adcMail"].isna()
    missing_email_count = int(students_with_no_email.sum())
    log.info(
        "removing students with no email",
        missing_email_count=missing_email_count,
    )
    if missing_email_count:
        print(
            src[students_with_no_email][
                ["weleveNomUsuel", "welevePrenomUsuel", "ElevesCursusActif::classe"]
            ].to_string(index=False, header=False)
        )
        src = src[~students_with_no_email]

    # Sanity check
    if not src["adcMail"].is_unique:
        print(src[src.duplicated()])
        sys.exit("Found duplicate emails in file. Exiting")

    res = pd.DataFrame()

    # We start with the columns that come from the source, thus creating all rows
    res["email"] = src["adcMail"]
    res["username"] = src["adcMail"].str.lower()
    res["firstname"] = src["welevePrenomUsuel"]
    res["lastname"] = src["weleveNomUsuel"]

    res["password"] = res["email"].map(email_to_password)

    # Every student gets this cohort
    res["cohort1"] = YEAR_PREFIX + "eleves"

    # One for the class
    res["cohort2"] = YEAR_PREFIX + src["ElevesCursusActif::classe"]

    #
    # Cohorts based on courses (options).
    #
    existing_cohorts = fetch_existing_moodle_cohorts(moodle)

    # We only keep the courses for which a cohort already exists in moodle,
    # thus filtering out all the "marker" courses the students were assigned in essaim.
    courses = src["ElevesCursusActif::xenclassDiscr"].str.split(" - ", expand=True)
    courses_with_matching_cohort_mask = courses.map(
        lambda course: YEAR_PREFIX + course in existing_cohorts
    )
    dropped_courses = courses[~courses_with_matching_cohort_mask]
    log.info(
        "dropped courses without a matching cohort",
        dropped=list(dropped_courses.melt()["value"].dropna().unique()),
    )

    courses = courses[courses_with_matching_cohort_mask]

    # Compact the columns of each row so that the NAs are squeezed-out
    courses = courses.apply(lambda x: pd.Series(x.dropna().values), axis=1)

    # Build cohorts from the courses
    course_cohorts = YEAR_PREFIX + courses

    # Assign proper names to these columns, starting with "cohort3"
    course_cohorts = course_cohorts.rename(lambda i: f"cohort{i + 3}", axis=1)

    res = pd.concat((res, course_cohorts), axis=1)
    log.info("done", student_count=len(res))

    return res


def fetch_existing_moodle_cohorts(moodle: MoodleClient) -> set[str]:
    result = moodle(
        "core_cohort_search_cohorts",
        query="",
        context={"contextlevel": "system"},
        includes="all",
        limitfrom=0,
        limitnum=10000,
    )
    cohorts = {c.name for c in result.cohorts}
    log.info("fetched all cohorts from moodle", cohort_count=len(cohorts))
    return cohorts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("essaim_students")
    parser.add_argument("moodle_students")
    args = parser.parse_args()

    dotenv.load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        sys.exit("Missing environment variable 'TOKEN'")
    salt = os.getenv("SALT")
    if not salt:
        sys.exit("Missing environment variable 'SALT'")

    log.info("connecting", url=URL)
    moodle = MoodleClient(URL, token)

    essaim_students = read_excel(args.essaim_students)
    transformed = transform(essaim_students, password_generator(salt), moodle)
    write_csv(transformed, args.moodle_students)
