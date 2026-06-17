"""
Takes:
- the id of the teachers cohort (the "Enseignants au gymnase de Beaulieu"
  cohort, whose id is 1)
- a csv obtained by running prepare_teachers_with_courses.py

compares the list of teachers found in moodle vs the list of teachers in the file

Uses the Moodle API
"""

import argparse

import polars as pl
import structlog

from lib.cohort import fetch_cohort_member_emails, report_email_diff
from lib.config import get_moodle_client
from lib.moodle_api import MoodleClient

log = structlog.get_logger()


def diff_teachers(moodle: MoodleClient, teachers_cohort_id: str, src: pl.DataFrame):
    existing = fetch_cohort_member_emails(moodle, teachers_cohort_id)

    wanted = set(src["email"])
    log.info("wanted teachers", count=len(wanted))

    report_email_diff(existing, wanted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("teachers_cohort_id")
    parser.add_argument("teachers_csv")

    args = parser.parse_args()

    wanted = pl.read_csv(args.teachers_csv)

    moodle = get_moodle_client()
    diff_teachers(moodle, args.teachers_cohort_id, wanted)
