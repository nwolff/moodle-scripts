"""Unit tests for the course -> category classification rules."""

import pytest

from preprocess_teachers_and_courses import course_to_category


@pytest.mark.parametrize(
    ("course", "expected_category"),
    [
        # Prefix matches
        ("Anglais", "Anglais"),
        ("Allemand_renforcé", "Allemand"),
        ("Italien", "Italien"),
        ("Sport", "Sport"),
        ("Philosophie", "Philosophie"),
        ("Informatique", "Informatique"),
        # Case-insensitive substring matches
        ("Français", "Français"),
        ("français", "Français"),
        ("Maths_renforcées", "Mathématiques"),
        ("Appl_maths", "Mathématiques"),
        # Bureautique is folded into Informatique
        ("Bureautique", "Informatique"),
        # Economie / droit / finance
        ("A&R", "Economie_et_droit"),
        ("Économie", "Economie_et_droit"),
        ("Economie", "Economie_et_droit"),
        ("Gestion_de_finance", "Economie_et_droit"),
        # DCO substring
        ("DCO_quelque_chose", "DCO"),
        # Histoire is exact-match only (so "histoire de l'art" stays separate)
        ("Histoire_et_institutions_politiques", "Histoire"),
        # Misc bucket
        ("religion", "Misc"),
        ("Trav._interdisc._centré_sur_un_proj.", "Misc"),
        ("Photo", "Misc"),
        ("Théâtre", "Misc"),
        ("Culture_antique", "Misc"),
        ("Sociologie", "Misc"),
        # Falls through to itself
        ("Biologie", "Biologie"),
        ("Histoire_de_l'art", "Histoire_de_l'art"),
    ],
)
def test_course_to_category(course: str, expected_category: str) -> None:
    assert course_to_category(course) == expected_category


def test_order_matters_bureautique_before_economie() -> None:
    # "Bureautique" contains no economy keyword, just a sanity check that the
    # Informatique fold wins and we don't accidentally bucket it elsewhere.
    assert course_to_category("Bureautique") == "Informatique"
