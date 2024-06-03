import re
import warnings

import pandas as pd

#  Input/Output tailored to our needs


def read_excel(path: str) -> pd.DataFrame:
    """
    Cells are read in as strings (and not the native excel cell types).
    """
    # From https://stackoverflow.com/questions/66214951
    with warnings.catch_warnings(record=True):
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            module=re.escape("openpyxl.styles.stylesheet"),
        )
        return pd.read_excel(path, dtype="string")


def write_excel(df: pd.DataFrame, path: str):
    """
    Write the dataframe to excel, without the initial index column.
    Cells are written as strings (and not the native excel cell types)
    NAs are written as empty cells
    """
    data_as_strings = df.astype(str).replace("<NA>", "")
    data_as_strings.to_excel(path, index=False)


def read_csv(path: str, sep: str = ",") -> pd.DataFrame:
    """
    Cells are read in as strings.
    """
    return pd.read_csv(path, sep=sep, engine="python", dtype="string")


def write_csv(df: pd.DataFrame, path: str):
    """
    Write the dataframe as csv, without the initial index column.
    """
    df.to_csv(path, index=False)
