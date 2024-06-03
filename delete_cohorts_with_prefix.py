#! /usr/bin/env python

"""
Deletes all cohorts that start with a given prefix.
The prefix should be something like "2324_".
Does 100 at a time, so you may need to run this script more than once.

We need this script because there is no bulk cohort delete in the moodle admin interface

Uses the Moodle API
"""

import argparse
import os
import sys

import dotenv
import structlog

from lib.moodle_api import URL, MoodleClient

log = structlog.get_logger()

BATCH_SIZE = 500


def delete_moodle_cohorts_with_prefix(moodle: MoodleClient, prefix: str):
    result = moodle(
        "core_cohort_search_cohorts",
        query=prefix,
        context={
            "contextid": 1
        },  # 1 is the system context (even though some docs say that is 10)
        limitfrom=0,
        limitnum=BATCH_SIZE,
    )
    cohorts_to_delete = result.cohorts

    if not cohorts_to_delete:
        print("No cohorts found, nothing to do")
        return
    for i, cohort in enumerate(cohorts_to_delete):
        log.info(
            "cohort",
            index=i,
            name=cohort.name,
        )

    print()
    user_input = input(
        f"Do you want to delete these {len(cohorts_to_delete)} cohorts (yes/no): "
    )
    if user_input.lower() != "yes":
        print("Aborting")
        sys.exit(0)

    cohort_ids_to_delete = [cohort.id for cohort in cohorts_to_delete]
    moodle("core_cohort_delete_cohorts", cohortids=cohort_ids_to_delete)
    log.info("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"Deletes {BATCH_SIZE} moodle cohorts that start with a prefix"
    )
    parser.add_argument("prefix")
    args = parser.parse_args()

    dotenv.load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        sys.exit("Missing environment variable 'TOKEN'")
    log.info("connecting", url=URL)
    moodle = MoodleClient(URL, token)

    delete_moodle_cohorts_with_prefix(moodle, args.prefix)
