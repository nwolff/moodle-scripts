"""
Takes:
- a top-level cohort id (for instance in 2526 the top-level cohort is
  2526_eleves and its id is 1821)
- a csv obtained by running prepare_students.py

compares the list of students found in moodle vs the list of students in the file

Uses the Moodle API
"""

import argparse

import polars as pl
import structlog

from lib.cohort import fetch_cohort_member_emails, report_email_diff
from lib.config import get_moodle_client
from lib.moodle_api import MoodleClient

log = structlog.get_logger()


def diff_students(moodle: MoodleClient, yearly_cohort_id: str, src: pl.DataFrame):
    existing = fetch_cohort_member_emails(moodle, yearly_cohort_id)

    wanted = set(src["email"])
    log.info("wanted students", count=len(wanted))

    report_email_diff(existing, wanted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("yearly_cohort_id")
    parser.add_argument("students_csv")

    args = parser.parse_args()

    wanted = pl.read_csv(args.students_csv)

    moodle = get_moodle_client()
    diff_students(moodle, args.yearly_cohort_id, wanted)
