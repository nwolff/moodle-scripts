"""
Behavioral tests for preprocess_teachers_and_courses.preprocess.

These act as a safety net around the heart of the project: the many
school-specific filtering, de-duplication, splitting and naming rules.

The input mirrors the shape of an essaim export (see the module docstring
of preprocess_teachers_and_courses), using the real `Maitre::*` column
names and a forward-filled teacher column (only the first row of each
teacher carries their identity, the rest are NULL).
"""

import polars as pl

from lib import schoolyear
from preprocess_teachers_and_courses import (
    CLASS,
    COURSE,
    COURSE_CATEGORY_PATH,
    COURSE_COHORT,
    COURSE_FULLNAME,
    COURSE_SHORTNAME,
    TEACHER_EMAIL,
    TEACHER_FIRSTNAME,
    TEACHER_LASTNAME,
    preprocess,
)

# Build the expected year fragments from the configured schoolyear so the
# tests keep passing when START_YYYY is bumped each year.
YEAR_SHORT = f"{schoolyear.START_YY}{schoolyear.END_YY}"  # e.g. "2627"
YEAR_FULL = f"{schoolyear.START_YYYY}-{schoolyear.END_YYYY}"  # e.g. "2026-2027"
YEAR_SHORT_DASH = f"{schoolyear.START_YY}-{schoolyear.END_YY}"  # e.g. "26-27"


def _row(sigle, nom, prenom, prenom_usuel, email, course):
    return {
        "Maitre::wsigle": sigle,
        "Maitre::wnom": nom,
        "Maitre::wprenom": prenom,
        "Maitre::prenomUsuel": prenom_usuel,
        "Maitre::wemail": email,
        "EnseignementProchain::wNoCoursLDAP": course,
    }


def make_input() -> pl.DataFrame:
    # The course code's leading fragment (the "2324" here) is always dropped,
    # so its exact value is irrelevant to the rules under test.
    rows = [
        # Teacher Mob: a kept maths course, then NULL-sigle rows that
        # forward-fill to him.
        _row("Mob", "Mould", "Bob", "B", "bmould@school.ch", "2324_3M08_Mathématiques"),
        _row(None, None, None, None, None, "2324_2M02_Physique"),
        # Exact duplicate of the previous course (half-class artifact) -> deduped
        _row(None, None, None, None, None, "2324_2M02_Physique"),
        # Filtered: TM class, Travail_personnel, Éducation_physique, Soutien class
        _row(None, None, None, None, None, "2324_TM1_Suivi"),
        _row(None, None, None, None, None, "2324_1C4_Travail_personnel"),
        _row(None, None, None, None, None, "2324_2M13_Éducation_physique"),
        _row(None, None, None, None, None, "2324_Soutien_Maths"),
        # Teacher ZZn: marker for an unknown teacher -> whole course filtered
        _row("Zzn", "ZZ_Name", None, None, None, "2324_3M13_Sport"),
        # Two teachers share an Informatique course for the same class:
        # these get split into two distinct Moodle courses (no cohort).
        _row("Aaa", "Alpha", "Anna", None, "alpha@school.ch", "2324_1C4_Informatique"),
        _row("Bbb", "Beta", "Bob", None, "beta@school.ch", "2324_1C4_Informatique"),
    ]
    return pl.DataFrame(rows)


def test_preprocess_golden():
    result = preprocess(make_input())
    by_shortname = {r[COURSE_SHORTNAME]: r for r in result.iter_rows(named=True)}

    # Exactly the four surviving courses, nothing filtered slipped through.
    assert set(by_shortname) == {
        f"{YEAR_SHORT}_3M08_Mathématiques",
        f"{YEAR_SHORT}_2M02_Physique",
        f"{YEAR_SHORT}_1C4_Informatique_Aaa",
        f"{YEAR_SHORT}_1C4_Informatique_Bbb",
    }

    maths = by_shortname[f"{YEAR_SHORT}_3M08_Mathématiques"]
    assert maths[CLASS] == "3M08"
    assert maths[COURSE] == "Mathématiques"
    assert maths[COURSE_FULLNAME] == f"Mathématiques 3M08 {YEAR_SHORT_DASH}"
    assert maths[COURSE_CATEGORY_PATH] == f"{YEAR_FULL} / Mathématiques"
    assert maths[COURSE_COHORT] == f"{YEAR_SHORT}_3M08"
    # Usual firstname ("B") is preferred over the official one ("Bob").
    assert maths[TEACHER_FIRSTNAME] == "B"
    assert maths[TEACHER_LASTNAME] == "Mould"
    assert maths[TEACHER_EMAIL] == "bmould@school.ch"

    physics = by_shortname[f"{YEAR_SHORT}_2M02_Physique"]
    assert physics[COURSE_CATEGORY_PATH] == f"{YEAR_FULL} / Physique"
    assert physics[COURSE_COHORT] == f"{YEAR_SHORT}_2M02"

    # Split courses: distinct shortnames, no cohort, firstname falls back to
    # the official first name (prenomUsuel is NULL for both).
    info_a = by_shortname[f"{YEAR_SHORT}_1C4_Informatique_Aaa"]
    info_b = by_shortname[f"{YEAR_SHORT}_1C4_Informatique_Bbb"]
    assert info_a[COURSE_COHORT] is None
    assert info_b[COURSE_COHORT] is None
    assert info_a[COURSE_CATEGORY_PATH] == f"{YEAR_FULL} / Informatique"
    assert info_a[COURSE_FULLNAME] == f"Informatique Aaa 1C4 {YEAR_SHORT_DASH}"
    assert info_a[TEACHER_FIRSTNAME] == "Anna"
    assert info_b[TEACHER_FIRSTNAME] == "Bob"


def test_preprocess_uses_actuel_column_when_prochain_absent():
    # "La bascule de l'année": when EnseignementProchain is missing, the data
    # lives in EnseignementActuel instead.
    src = pl.DataFrame(
        [
            {
                "Maitre::wsigle": "Mob",
                "Maitre::wnom": "Mould",
                "Maitre::wprenom": "Bob",
                "Maitre::prenomUsuel": "B",
                "Maitre::wemail": "bmould@school.ch",
                "EnseignementActuel::wNoCoursLDAP": "2324_3M08_Mathématiques",
            }
        ]
    )
    result = preprocess(src)
    assert result[COURSE_SHORTNAME].to_list() == [f"{YEAR_SHORT}_3M08_Mathématiques"]
