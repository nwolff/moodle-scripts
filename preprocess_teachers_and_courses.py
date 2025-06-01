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

import polars as pl
import structlog

from lib import schoolyear

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


def preprocess(src: pl.DataFrame) -> pl.DataFrame:
    log.info(
        "start",
        num_courses=len(src),
        unique_teachers=len(src["Maitre::wnom"].unique()),
    )

    ###
    # 1. Start with the teacher info.
    ###
    teacher_info_lookup = pl.DataFrame()

    teacher_info_lookup[[TEACHER_TLA, TEACHER_LASTNAME, TEACHER_EMAIL]] = src[
        "Maitre::wsigle", "Maitre::wnom", "Maitre::wemail"
    ]

    # Usual firstname with fallback to the official one
    teacher_info_lookup = teacher_info_lookup.with_columns(
        src["Maitre::prenomUsuel"]
        .fill_null(src["Maitre::wprenom"])
        .alias(TEACHER_FIRSTNAME)
    )

    teacher_info_lookup = teacher_info_lookup.filter(~pl.col(TEACHER_TLA).is_null())

    ###
    # 2. Unpack course and class information
    ###
    # First find out in which column the data lives depending on "la bascule de l'année"
    course_column = None
    if "EnseignementProchain::wNoCoursLDAP" in src.columns:
        course_column = "EnseignementProchain::wNoCoursLDAP"
    else:
        course_column = "EnseignementActuel::wNoCoursLDAP"

    res = pl.DataFrame()
    res = res.with_columns(
        src["Maitre::wsigle"].alias(TEACHER_TLA),
        temp=src[course_column]
        .map_elements(
            lambda c: c.split("_", maxsplit=2)[1:], return_dtype=pl.List(pl.String)
        )
        .list.to_struct(fields=[CLASS, COURSE]),
    ).unnest("temp")

    res = res.with_columns(pl.col(TEACHER_TLA).fill_null(strategy="forward"))

    res = res.join(teacher_info_lookup, on=TEACHER_TLA, maintain_order="left")

    ###
    # 4. Remove lines that won't become a course in Moodle
    ###

    res = res.drop_nulls(subset=[COURSE])
    log.info("done removing empty courses", num_courses=len(res))

    res = res.filter(~res[COURSE].str.contains("Travail_personnel"))
    log.info(
        "done removing courses containing 'Travail_personnel'", num_courses=len(res)
    )

    res = res.filter(~(res[COURSE] == "Éducation_physique"))
    log.info("done removing 'Éducation_physique' courses", num_courses=len(res))

    # TM* Classes don't need a course.
    res = res.filter(~res[CLASS].str.starts_with("TM"))
    log.info("done removing courses for TM* classes", num_courses=len(res))

    # ZZ is a marker for when we don't know who will be giving a class.
    # We don't create a course in moodle for those.
    res = res.filter(~res[TEACHER_LASTNAME].str.starts_with("ZZ"))
    log.info("done removing courses for ZZ* teachers", num_courses=len(res))

    # Remove duplicate courses for a teacher
    # These duplicates in the input appear when the class is split into half-class groups
    # (it depends on how Emmanuel configured things in essaim, sometimes we get these duplicates, sometimes we don't)
    # We assume the teacher only wants a single Moodle course for both groups.
    res = res.unique(maintain_order=True)
    log.info("done removing duplicate courses for a teacher", num_courses=len(res))

    ###
    # 5. Split some of the courses shared between two teachers
    ###

    log.info("splitting some of the courses that are shared between teachers...")

    res = res.with_row_index()  # We use the index to mark which courses should be split. Add it once to the dataframe

    # These are the type of courses that when shared between multipler teachers, will get two separate moodle courses
    split_candidates = res.filter(res[COURSE].is_in(("Bureautique", "Informatique")))

    # Find all the courses where class and course are duplicated (but not the teacher, we took care of those just above)
    need_split = split_candidates.filter(
        split_candidates.select([CLASS, COURSE]).is_duplicated()
    )

    need_split_index = need_split["index"].implode()
    res = res.with_columns(
        pl.when(pl.col("index").is_in(need_split_index))
        .then(pl.col(COURSE) + "_" + pl.col(TEACHER_TLA))
        .otherwise(pl.col(COURSE))
        .alias(COURSE),
        pl.when(pl.col("index").is_in(need_split_index))
        .then(pl.lit(None))
        .otherwise(f"{schoolyear.START_YY}{schoolyear.END_YY}" + "_" + res[CLASS])
        .alias(COURSE_COHORT),
    )

    # Print result of split
    with pl.Config(tbl_rows=-1):
        print(
            res.filter(pl.col("index").is_in(need_split_index))
            .sort(CLASS)
            .select([TEACHER_TLA, CLASS, COURSE, COURSE_COHORT])
        )
    print()

    ###
    # 6. Fill-in derived fields
    ###

    res = res.with_columns(
        (
            f"{schoolyear.START_YY}{schoolyear.END_YY}"
            + "_"
            + res[CLASS]
            + "_"
            + res[COURSE]
        ).alias(COURSE_SHORTNAME)
    )

    res = res.with_columns(
        (
            res[COURSE].str.replace_all("_", " ")
            + " "
            + res[CLASS]
            + " "
            + f"{schoolyear.START_YY}-{schoolyear.END_YY}"
        ).alias(COURSE_FULLNAME)
    )

    res = res.with_columns(
        (
            f"{schoolyear.START_YYYY}-{schoolyear.END_YYYY}"
            + " / "
            + res[COURSE].map_elements(course_to_category, return_dtype=pl.String)
        ).alias(COURSE_CATEGORY_PATH)
    )

    ###
    # 7. Remove temporary fields
    ###
    res = res[ALL_FIELDS]

    log.info("done", num_courses=len(res))

    return res


def course_to_category(s: str) -> str:
    """
    We create these categories only to help navigate inside the large number of courses in moodle.
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

    teachers_and_courses = pl.read_excel(args.teachers_and_courses)
    output = preprocess(teachers_and_courses)

    # Dump categories to get a feel of how we classified things
    print()
    print("Categories: ")
    print()
    categories = output[COURSE_CATEGORY_PATH].unique()
    categories.sort()
    for cat in categories:
        print(cat)

    output.write_csv(args.output)
