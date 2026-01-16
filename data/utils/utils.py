"""Utilities for ETL Pipeline"""
import re

import pandas as pd

from data.models.choices import SexKaryotype


def standardise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardises DataFrame column names to snake_case following PEP8.
    """
    cols = (
        df.columns.str.strip()
        .str.lower()
        .str.replace("%", "_pct_", regex=False)
        .str.replace(r"[\s\W]+", "_", regex=True)
        .str.replace(r"_+", "_", regex=True)
        .str.strip("_")
    )

    # De-duplicate column names to prevent errors
    duplicates = cols.to_series().groupby(cols).cumcount()
    cols = cols.where(duplicates == 0, cols + "_" + duplicates.astype(str))

    df.columns = cols
    return df


def coerce_data_types(
    df: pd.DataFrame,
    max_categories: int = 10,
    cardinality: float = 0.05,
) -> pd.DataFrame:
    """
    Coerces DataFrame columns to more appropriate dtypes.
    - Uses pandas `convert_dtypes` to infer best possible dtypes.
    - Converts columns with low cardinality to 'category' type.
    """
    n_rows = len(df)
    if n_rows == 0:
        return df

    df = df.convert_dtypes()

    candidate_cols = df.select_dtypes(include=["string", "integer"]).columns

    for col in candidate_cols:
        num_unique = df[col].nunique(dropna=True)

        # skip trivial (all same / all unique)
        if num_unique == 1 or num_unique == n_rows:
            continue

        # check both absolute and relative thresholds
        if num_unique <= max_categories and (num_unique / n_rows) <= cardinality:
            df[col] = df[col].astype("category")

    return df


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = standardise_column_names(df)
    df = coerce_data_types(df)

    return df.where(pd.notna(df), None)


def get_sample_metadata(name: str) -> dict:
    """Extracts metadata from a sample name."""
    
    control_pattern = r"-[0-9]+Q[0-9]+-|NA\d+.*|HG00.*"
    is_control = bool(re.search(control_pattern, name))

    batch = ""
    testcode = None
    sex = SexKaryotype.UNKNOWN

    parts = name.split("-")

    # Extract batch, testcode, and sex from sample name

    # Case 1: Handle HRD naming convention (...-25-HRDS11-9197-F)
    if len(parts) >= 7 and "HRD" in parts[-3]:
        sex = SexKaryotype(parts[-1])
        testcode = parts[-2]
        batch = parts[-3]

    # Case 2: Handle standard naming convention (...-BATCH-TESTCODE-SEX-...)
    elif len(parts) >= 6:
        sex = SexKaryotype(parts[-2])
        testcode = parts[-3]
        batch = parts[-4]

    # Case 3: Handle naming convention for Helios (...-BATCH-TESTCODE)
    elif len(parts) >= 4:
        if parts[-1].isdigit() and len(parts[-1]) >= 4:
            testcode = parts[-1]
            batch = parts[-2]

    if testcode and testcode.isdigit():
        testcode = int(testcode)
    else:
        testcode = None  # Ensure testcode is None if not a valid integer
        
    return {
            "is_control": is_control,
            "sex": sex,
            "batch": batch,
            "testcode": testcode,
        }