"""
Deletes all cohorts that start with a given prefix.
The prefix should be something like "2324_".

We need this script because there is no bulk cohort delete in the moodle admin interface

Uses the Moodle API
"""

import argparse
import sys

import structlog

from lib.config import get_moodle_client
from lib.moodle_api import MoodleClient

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

    moodle = get_moodle_client()

    delete_moodle_cohorts_with_prefix(moodle, args.prefix)
