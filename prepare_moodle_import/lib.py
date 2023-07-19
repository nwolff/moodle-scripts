import warnings

import pandas as pd

YEAR_PREFIX = "2324_"  # XXX. Change this every year


def read_excel(path: str) -> pd.DataFrame:
    """
    Cells are read in as strings (and not the native excel file types).
    """
    # https://stackoverflow.com/questions/66214951
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        return pd.read_excel(path, dtype="string")


def read_csv(path: str, sep=","):
    """
    Cells are read in as strings (and not the native excel file types).
    """
    return pd.read_csv(path, sep=sep, engine="python", dtype="string")


def write_csv(df: pd.DataFrame, path: str):
    """
    Write the dataframe as csv, without the initial index column.
    """
    df.to_csv(path, index=False)


def prefix_year(s):
    """
    Prefixes the string s with the current year prefix
    unless s is undefined/empty.
    """
    return s if pd.isna(s) else YEAR_PREFIX + s


def prefixed_courses_list(s: str) -> list[str]:
    """
    Given a "-" separated string, returns a list of course names:
    - Where the non-courses have been filtered out
    - Where the course names are prefixed with the year
    """
    UNWANTED_COURSES = ["Sa", "Pé", "CI", "SP"]  # C specialities (including old)
    UNWANTED_COURSES += ["TM"]  # Obviously not a course
    UNWANTED_COURSES += ["Al", "An", "AV", "Mu"]  # M Language and arts options
    UNWANTED_COURSES += ["NS", "NR"]  # Don't know what these are
    if pd.isna(s):
        courses = []
    else:
        courses = [course.strip() for course in s.split("-")]
    return [prefix_year(c) for c in courses if c not in UNWANTED_COURSES]


def nth_or_none(index: int):
    """
    Returns a function that takes a list and returns:
     - the index element of the list if it exists
     - otherwise None
    Useful as an argument to pandas.Series.map()
    """
    return lambda lst: lst[index] if index < len(lst) else None
