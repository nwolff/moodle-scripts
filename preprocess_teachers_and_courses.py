#! /usr/bin/env python

"""
Takes an essaim export of teachers and courses that looks like this:
(Note that the first 4 lines are for teacher "Bob Mould")

Maitre::sigle   Maitre::wnom	Maitre::wprenom	    Maitre::prenomUsuel     Maitre::wemail	        EnseignementProchain::wNoCoursLDAP

Mob             Mould	        Bob	                B                       bmould@school.ch	    2324_3M08_Mathématiques_(niveau_standard)
NULL            NULL	        NULL	            NULL                    NULL	                2324_2M02_Physique
NULL            NULL	        NULL	            NULL                    NULL	                2324_2M13_Physique
NULL            NULL	        NULL	            NULL                    NULL	                2324_1C4_Physique
Zzn             ZZ_Name	        NULL	            NULL                    NULL	                2324_3M13_Sport
NULL            NULL	        NULL	            NULL                    NULL	                2324_2CSA2_Sport


Also takes an essaim export that associates the teachers sigle with their pédago login.
The sigle is the primary key for teachers in essaim.


Generates a file that is be used by the other tools.
Constants with the column names are also exported by this file,
to avoid to avoid typos when accessing them

All business rules are encapsulated here :
- How the teacher's first name is built from the name and usual name
- The rules for classes and courses that don't get a matching entity in Moodle
- The classification of courses into categories
- The precise naming conventions for courses, categories, and cohorts
- The fact that we delete duplicate courses for a single teacher. These duplicates
 in the input means the class is split into half-class groups, we assume the
 teacher only needs a single Moodle course for both groups
 - The way we select which duplicate courses to split into one course per teacher
"""

import argparse

import pandas as pd
import structlog

from lib import schoolyear
from lib.io import read_excel, write_csv

log = structlog.get_logger()

TEACHER_TLA = "teacher_tla"
TEACHER_LASTNAME = "teacher_lastname"
TEACHER_FIRSTNAME = "teacher_firstname"
TEACHER_EMAIL = "teacher_email"
TEACHER_PEDAGO_LOGIN = "teacher_pedago_login"
CLASS = "class"
COURSE = "course"
COURSE_SHORTNAME = "shortname"
COURSE_FULLNAME = "fullname"
COURSE_CATEGORY_PATH = "category_path"
COURSE_COHORT = "cohort"

ALL_FIELDS = [
    TEACHER_TLA,
    TEACHER_LASTNAME,
    TEACHER_FIRSTNAME,
    TEACHER_EMAIL,
    TEACHER_PEDAGO_LOGIN,
    CLASS,
    COURSE,
    COURSE_SHORTNAME,
    COURSE_FULLNAME,
    COURSE_CATEGORY_PATH,
    COURSE_COHORT,
]


def preprocess(src: pd.DataFrame, login_and_email: pd.DataFrame) -> pd.DataFrame:
    log.info(
        "start",
        number_of_courses=len(src),
        unique_teachers=len(src["Maitre::wnom"].unique()),
    )

    res = pd.DataFrame()

    ###
    # Start with the teacher info.
    ###

    res[[TEACHER_TLA, TEACHER_LASTNAME, TEACHER_EMAIL]] = src[
        ["Maitre::wsigle", "Maitre::wnom", "Maitre::wemail"]
    ]

    # usual firstname with fallback to the official one
    res[TEACHER_FIRSTNAME] = src["Maitre::prenomUsuel"].fillna(src["Maitre::wprenom"])

    # Data comes grouped by teacher, but the teacher info is only present on the first course for that teacher.
    # We need to repeat the data down for each course of the teacher.
    # We can't use ffill because that would spill the info of the last teacher into the ZZ lines where the
    # teacher firstname and emails are missing.
    last_tla, last_lastname, last_firstname, last_email = None, None, None, None
    for i, row in res.iterrows():
        if pd.isna(row[TEACHER_TLA]):
            res.at[i, TEACHER_TLA] = last_tla
            res.at[i, TEACHER_LASTNAME] = last_lastname
            res.at[i, TEACHER_FIRSTNAME] = last_firstname
            res.at[i, TEACHER_EMAIL] = last_email
        else:
            last_tla = row[TEACHER_TLA]
            last_lastname = row[TEACHER_LASTNAME]
            last_firstname = row[TEACHER_FIRSTNAME]
            last_email = row[TEACHER_EMAIL]

    log.info("done unfolding", unfolded_size=len(res))

    ###
    # Merge-in the pedago login
    ###

    # Data in essaim is dirty, there are many lines without a sigle
    login_and_email = login_and_email.dropna(subset=["Maitres::wsigle"])
    res = res.join(login_and_email.set_index("Maitres::wsigle"), on=TEACHER_TLA)
    res = res.rename(columns={"pedagoLogin": TEACHER_PEDAGO_LOGIN})
    log.info("done merging login and email info", merged_size=len(res))

    ###
    # Unpack course and class information
    ###
    split_course_info = src["EnseignementProchain::wNoCoursLDAP"].str.split(
        "_", n=2, expand=True
    )
    res[[CLASS, COURSE]] = split_course_info.drop(0, axis="columns")

    ###
    # Remove lines that won't become a course in Moodle
    ###

    # Courses
    res = res.dropna(subset=[COURSE])
    log.info("done removing empty courses", num_courses=len(res))

    res = res[~res[COURSE].str.contains("Travail_personnel")]
    log.info("done removing courses containing Travail_personnel", num_courses=len(res))

    res = res[~(res[COURSE] == "Éducation_physique")]
    log.info("done removing 'Éducation_physique' courses", num_courses=len(res))

    # Classes
    res = res[~res[CLASS].str.startswith("TM")]
    log.info("done removing courses for TM* classes", num_courses=len(res))

    # Teachers
    res = res[~res[TEACHER_LASTNAME].str.startswith("ZZ")]
    log.info("done removing courses for ZZ teachers", num_courses=len(res))

    ###
    # Remove duplicate courses for a teacher
    ###
    log.info("removing duplicate courses for a teacher...")
    print(res[res.duplicated()][[TEACHER_TLA, CLASS, COURSE]])
    res = res.drop_duplicates()
    log.info("done removing duplicate courses for a teacher", num_courses=len(res))

    ###
    # Split some of the courses shared between two teachers
    ###
    log.info("splitting Bureautique courses shared between teachers...")
    dupes = res[res.duplicated(subset=[CLASS, COURSE], keep=False)][
        [TEACHER_TLA, CLASS, COURSE]
    ]
    dedupe = dupes[dupes[COURSE] == "Bureautique"]
    res.loc[dedupe.index, CLASS] += res[TEACHER_TLA]
    print(res.loc[dedupe.index].sort_values([CLASS])[[TEACHER_TLA, CLASS, COURSE]])
    log.info(
        "done splitting Bureautique courses shared between teachers",
        num_courses=len(res),
    )

    ###
    # Fill-in derived fields
    ###

    res[COURSE_SHORTNAME] = (
        f"{schoolyear.START_YY}{schoolyear.END_YY}"
        + "_"
        + res[CLASS]
        + "_"
        + res[COURSE]
    )

    res[COURSE_FULLNAME] = (
        res[COURSE].str.replace("_", " ")
        + " "
        + res[CLASS]
        + " "
        + f"{schoolyear.START_YY}-{schoolyear.END_YY}"
    )

    res[COURSE_CATEGORY_PATH] = (
        f"{schoolyear.START_YYYY}-{schoolyear.END_YYYY}"
        + " / "
        + res[COURSE].map(course_to_category)
    )

    res[COURSE_COHORT] = f"{schoolyear.START_YY}{schoolyear.END_YY}" + "_" + res[CLASS]

    ###
    # Remove temporary fields
    ###
    res = res[ALL_FIELDS]

    return res


def course_to_category(s: str) -> str:
    """
    We create these categories only to help
    navigate inside the large number of courses.
    """
    # Order of matches is important
    prefixes = (
        "Anglais",
        "Allemand",
        "Italien",
        "Sport",
        "Philosophie",
        "Informatique",
    )
    for prefix in prefixes:
        if s.startswith(prefix):
            return prefix
    if "français" in s.lower():
        return "Français"
    if "math" in s.lower():
        return "Mathématiques"
    if "bureautique" in s.lower():
        return "Informatique"
    if s.startswith("A&R") or s == "Economie_et_droit" or "finance" in s.lower():
        return "Économie_et_droit"
    if s.startswith("DCO"):
        return "DCO"
    # We don't just match on "histoire" because "histoire de l'art" is in its own category
    if s == "Histoire_et_institutions_politiques":
        return "Histoire"
    if "relig" in s or s in ("Photo", "Théâtre", "Culture_antique", "Sociologie"):
        return "Misc"
    return s


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("teachers_and_courses")
    parser.add_argument("login_and_email")
    parser.add_argument("output")
    args = parser.parse_args()

    teachers_and_courses = read_excel(args.teachers_and_courses)
    login_and_email = read_excel(args.login_and_email)
    output = preprocess(src=teachers_and_courses, login_and_email=login_and_email)
    write_csv(output, args.output)
