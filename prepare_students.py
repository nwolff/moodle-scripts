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
from collections.abc import Callable

import dotenv
import polars as pl
import structlog

from lib.moodle_api import URL, MoodleClient
from lib.passwords import password_generator
from lib.schoolyear import END_YY, START_YY

log = structlog.get_logger()

YEAR_PREFIX = f"{START_YY}{END_YY}_"


def transform(
    src: pl.DataFrame, email_to_password: Callable[[str], str], moodle: MoodleClient
) -> pl.DataFrame:
    log.info("start", student_count=len(src))

    # Some students don't have an email address (yet),
    # so we can't create their moodle account
    students_with_no_email = src["adcMail"].is_null()
    missing_email_count = int(students_with_no_email.sum())
    log.info(
        "removing students with no email",
        missing_email_count=missing_email_count,
    )
    if missing_email_count:
        with pl.Config() as cfg:
            cfg.set_tbl_rows(-1)
            cfg.set_tbl_hide_dataframe_shape(True)
            cfg.set_tbl_hide_column_names(True)
            cfg.set_tbl_hide_column_data_types(True)
            cfg.set_tbl_formatting("NOTHING")
            print(
                src.filter(students_with_no_email).select(
                    "weleveNomUsuel", "welevePrenomUsuel", "ElevesCursusActif::classe"
                )
            )
        src = src.filter(~students_with_no_email)
        log.info("after removing missing emails", student_count=len(src))

    # Sanity check
    duplicate_emails = src["adcMail"].is_duplicated()
    if duplicate_emails.any():
        print("Found duplicates emails: ")
        print(src.filter(duplicate_emails))
        sys.exit("Exiting")

    # The only 4th year students that are taught in Beaulieu are the 4MSOP,
    # We filter all others because we need to keep the numbers low in moodle so we don't blow up our plan.
    # Currently these are the 4E, 4MSCI, 4MSSA
    students_not_attending_here = src["ElevesCursusActif::classe"].is_in(
        ["4E1", "4MSCI1", "4MSSA1", "4MSSA2"]
    )
    students_not_attending_here_count = int(students_not_attending_here.sum())
    log.info(
        "removing students not attending here",
        students_not_attending_here=students_not_attending_here_count,
    )
    src = src.filter(~students_not_attending_here)
    log.info("after removing students not attending here", student_count=len(src))

    # Build up most of the data
    res = pl.DataFrame().with_columns(
        email=src["adcMail"],
        username=src["adcMail"].str.to_lowercase(),
        firstname=src["welevePrenomUsuel"],
        lastname=src["weleveNomUsuel"],
        password=src["adcMail"].map_elements(email_to_password, return_dtype=pl.String),
        cohort1=pl.lit(YEAR_PREFIX + "eleves"),
        cohort2=pl.concat_str(pl.lit(YEAR_PREFIX), src["ElevesCursusActif::classe"]),
        courses=src["ElevesCursusActif::xenclassDiscr"].str.split(" - "),
    )

    # Prefix the year to the courses list
    res = res.with_columns(pl.col("courses").list.eval(YEAR_PREFIX + pl.element()))

    # Only keep the courses for which a cohort already exists in moodle,
    # thus filtering out all the "marker" courses the students were assigned in essaim.
    existing_cohorts = fetch_existing_moodle_cohorts(moodle)
    res = res.with_columns(
        pl.col("courses").list.filter(pl.element().is_in(existing_cohorts))
    )

    # Create columns starting with name "cohort3" for the remaining courses
    res = res.with_columns(
        pl.col("courses").list.to_struct(
            n_field_strategy="max_width",
            fields=lambda idx: f"cohort{idx + 3}",  # Start with cohort3
        )
    ).unnest("courses")

    log.info("done", student_counts=len(res))

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

    essaim_students = pl.read_excel(args.essaim_students)
    transformed = transform(essaim_students, password_generator(salt), moodle)
    transformed.write_csv(args.moodle_students)
