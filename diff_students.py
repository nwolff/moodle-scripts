"""
Takes:
- a top-level cohort id (for instance in 2526 the top-level cohort is 2526_eleves and its id is 1821)
- a csv obtained by running prepare_students.py

compares the list of students found in moodle vs the list of students in the file

Uses the Moodle API
"""

import argparse
import os
import sys

import dotenv
import polars as pl
import structlog

from lib.moodle_api import URL, MoodleClient

log = structlog.get_logger()


def diff_students(moodle: MoodleClient, yearly_cohort_id: str, src: pl.DataFrame):
    response = moodle(
        "core_cohort_get_cohort_members",
        cohortids=[yearly_cohort_id],
    )
    existing_students_ids = response[0].userids

    log.info(
        "got student ids for cohort",
        cohort_id=yearly_cohort_id,
        student_count=len(existing_students_ids),
    )

    log.info("retrieving students info...", student_id_count=len(existing_students_ids))
    response = moodle(
        "core_user_get_users_by_field", field="id", values=existing_students_ids
    )

    log.info("got student info", student_info_count=len(response))

    existing = {s.email for s in response}

    log.info("unique emails", count=len(existing))

    wanted = set(src["email"])
    log.info("wanted students", count=len(wanted))

    # We just display these, in case the user wants to remove them
    extra = sorted(existing - wanted)
    log.info("in moodle but not in file", students=extra)

    missing = sorted(wanted - existing)
    log.info("in file but not in moodle", students=missing)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("yearly_cohort_id")
    parser.add_argument("students_csv")

    args = parser.parse_args()

    dotenv.load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        sys.exit("Missing environment variable 'TOKEN'")

    wanted = pl.read_csv(args.students_csv)

    log.debug("connecting", url=URL, token=token)
    moodle = MoodleClient(URL, token)
    diff_students(moodle, args.yearly_cohort_id, wanted)
