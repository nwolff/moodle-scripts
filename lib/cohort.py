"""
Helpers for comparing the members of a Moodle cohort against a prepared
import file, by email address.

Shared by diff_students.py and diff_teachers.py, which both answer the same
question: which people are in the cohort but not the file (candidates for
removal), and which are in the file but not yet in Moodle.
"""

import structlog

from lib.moodle_api import MoodleClient

log = structlog.get_logger()


def fetch_cohort_member_emails(moodle: MoodleClient, cohort_id: str) -> set[str]:
    """Return the set of email addresses of the members of a cohort."""
    response = moodle("core_cohort_get_cohort_members", cohortids=[cohort_id])
    member_ids = response[0].userids
    log.info(
        "got member ids for cohort",
        cohort_id=cohort_id,
        member_count=len(member_ids),
    )

    response = moodle("core_user_get_users_by_field", field="id", values=member_ids)
    emails = {u.email for u in response}
    log.info("got member emails", email_count=len(emails))
    return emails


def report_email_diff(existing: set[str], wanted: set[str]) -> None:
    """Log the symmetric difference between the cohort and the file."""
    # We just display these, in case the user wants to remove them
    extra = sorted(existing - wanted)
    log.info("in moodle but not in file", count=len(extra), emails=extra)

    missing = sorted(wanted - existing)
    log.info("in file but not in moodle", count=len(missing), emails=missing)
