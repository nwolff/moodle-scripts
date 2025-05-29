#! /usr/bin/env python

"""
Takes an essaim export of teachers and courses that looks like this:
(Note that the first 4 lines are for teacher "Mob", the last two ones for "ZZn")

Maitre::sigle   Maitre::wnom	Maitre::wprenom	    Maitre::prenomUsuel     Maitre::wemail	        EnseignementProchain::wNoCoursLDAP Or
                                                                                                    EnseignementActuel::wNoCoursLDAP

Mob             Mould	        Bob	                B                       bmould@school.ch	    2324_3M08_Mathématiques_(niveau_standard)
NULL            NULL	        NULL	            NULL                    NULL	                2324_2M02_Physique
NULL            NULL	        NULL	            NULL                    NULL	                2324_2M13_Physique
NULL            NULL	        NULL	            NULL                    NULL	                2324_1C4_Physique
Zzn             ZZ_Name	        NULL	            NULL                    NULL	                2324_3M13_Sport
NULL            NULL	        NULL	            NULL                    NULL	                2324_2CSA2_Sport


All business rules are implemented here:
- How the teacher's first name is built from the name and usual name
- The rules for classes and courses that wont become something in Moodle
- The way courses with multiple teachers are mapped to moodle courses:
    - Either they become two separate courses (when the class is split in two all the time)
    - Or they become a single moodle course with two teachers.
- The classification of courses into categories
- The precise naming conventions for courses, categories, and cohorts


All other tools feed from the output of this file, using the column names defined in ALL_FIELDS to access information

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
    CLASS,
    COURSE,
    COURSE_SHORTNAME,
    COURSE_FULLNAME,
    COURSE_CATEGORY_PATH,
    COURSE_COHORT,
]


def preprocess(src: pd.DataFrame) -> pd.DataFrame:
    log.info(
        "start",
        num_courses=len(src),
        unique_teachers=len(src["Maitre::wnom"].unique()),
    )

    res = pd.DataFrame()

    ###
    # 1. Start with the teacher info.
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

    ###
    # 2. Unpack course and class information
    ###

    # First find out in which column the data lives.
    # Before "la bascule de l'année" it's in EnseignementProchain::wNoCoursLDAP,
    # afterwards in EnseignementActuel::wNoCoursLDAP
    course_column = None
    if "EnseignementProchain::wNoCoursLDAP" in src.columns:
        course_column = "EnseignementProchain::wNoCoursLDAP"
    else:
        course_column = "EnseignementActuel::wNoCoursLDAP"

    split_course_info = src[course_column].str.split("_", n=2, expand=True)
    res[[CLASS, COURSE]] = split_course_info.drop(0, axis="columns")

    ###
    # 3. Remove lines that won't become a course in Moodle
    ###

    res = res.dropna(subset=[COURSE])
    log.info("done removing empty courses", num_courses=len(res))

    res = res[~res[COURSE].str.contains("Travail_personnel")]
    log.info(
        "done removing courses containing 'Travail_personnel'", num_courses=len(res)
    )

    res = res[~(res[COURSE] == "Éducation_physique")]
    log.info("done removing 'Éducation_physique' courses", num_courses=len(res))

    # TM* Classes don't need a course.
    res = res[~res[CLASS].str.startswith("TM")]
    log.info("done removing courses for TM* classes", num_courses=len(res))

    # ZZ is a marker for when we don't know who will be giving a class.
    # We don't create a course in moodle for those.
    res = res[~res[TEACHER_LASTNAME].str.startswith("ZZ")]
    log.info("done removing courses for ZZ* teachers", num_courses=len(res))

    # Remove duplicate courses for a teacher
    # These duplicates in the input appear when the class is split into half-class groups
    # (it depends on how Emmanuel configured things in essaim, sometimes we get these duplicates, sometimes we don't)
    # We assume the teacher only wants a single Moodle course for both groups.
    # log.info("removing duplicate courses for a teacher...")
    # print(res[res.duplicated()][[TEACHER_TLA, CLASS, COURSE]])
    res = res.drop_duplicates()
    log.info("done removing duplicate courses for a teacher", num_courses=len(res))

    ###
    # 4. Split some of the courses shared between two teachers
    ###
    log.info("splitting some of the courses that are shared between teachers...")
    shared = res[res.duplicated(subset=[CLASS, COURSE], keep=False)][
        [TEACHER_TLA, CLASS, COURSE]
    ]
    # print(shared)

    # Only some of the shared courses get two separate moodle courses
    split = shared[shared[COURSE].isin(("Bureautique", "Informatique"))]
    res.loc[split.index, COURSE] += "_" + res[TEACHER_TLA]

    # We don't want to create cohorts for these courses, because essaim does not know their composition.
    # The teacher will need to manually enroll students.
    res.loc[split.index, COURSE_COHORT] = ""

    print(res.loc[split.index].sort_values([CLASS])[[TEACHER_TLA, CLASS, COURSE]])
    print()

    ###
    # 5. Fill-in derived fields
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

    res.loc[res[COURSE_COHORT].isna(), COURSE_COHORT] = (
        f"{schoolyear.START_YY}{schoolyear.END_YY}" + "_" + res[CLASS]
    )

    ###
    # 6. Remove temporary fields
    ###
    res = res[ALL_FIELDS]

    return res


def course_to_category(s: str) -> str:
    """
    We create these categories only to help
    navigate inside the large number of courses in moodle.
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
    if s.startswith(("A&R", "Économie", "Economie")) or "finance" in s.lower():
        return "Economie_et_droit"
    if s.startswith("DCO"):
        return "DCO"
    # We don't just match on "histoire" because "histoire de l'art" is in its own category
    if s == "Histoire_et_institutions_politiques":
        return "Histoire"
    if (
        "relig" in s
        or "Trav._interdisc._centré_sur_un_proj." in s
        or s in ("Photo", "Théâtre", "Culture_antique", "Sociologie")
    ):
        return "Misc"
    return s


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("teachers_and_courses")
    parser.add_argument("output")
    args = parser.parse_args()

    teachers_and_courses = read_excel(args.teachers_and_courses)
    output = preprocess(teachers_and_courses)

    # Dump categories to get a feel of how we classified things
    print("Categories: ")
    categories = output[COURSE_CATEGORY_PATH].unique()
    categories.sort()
    for cat in categories:
        print(cat)

    write_csv(output, args.output)
