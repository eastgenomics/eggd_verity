import re

import pandas as pd

from data.models.choices import QCStatus, SexKaryotype


def format_categorical_columns(
    df: pd.DataFrame,
    color_by: str | None = None,
    symbol_by: str | None = None,
    grouping_args: dict | None = None,
) -> pd.DataFrame:
    """
    Converts integer enum values in a DataFrame to their string representations.
    """
    if grouping_args is None:
        grouping_args = {}

    enum_map = {
        "qc_status": QCStatus,
        "sex": SexKaryotype,
        "gender": SexKaryotype,
        "reported_sex": SexKaryotype,
        "predicted_sex": SexKaryotype,
        "original_pedigree_sex": SexKaryotype,
    }

    for arg_name, arg_val in [("color", color_by), ("symbol", symbol_by)]:
        if arg_val:
            _model_name, field_name = arg_val.split(".")
            if field_name in enum_map:
                enum_class = enum_map[field_name]
                column_alias = grouping_args.get(arg_name)
                if column_alias and column_alias in df.columns:
                    df[column_alias] = df[column_alias].apply(
                        lambda x: str(enum_class(x)) if pd.notna(x) else "N/A"
                    )
    return df


def run_label(project_name: str) -> str:
    """
    Short label for a run: the project name without its leading number prefix.
    e.g. '002_261016_A01295_0866_BHV232DRX7_HRD' -> '261016_A01295_0866_BHV232DRX7_HRD'
    """
    # Only a short prefix followed by the YYMMDD run date, so that a name that
    # already starts with the date is left alone
    return re.sub(r"^\d{1,4}_(?=\d{6}_)", "", str(project_name))


def run_sample_counts(df: pd.DataFrame, value_col: str, by=()) -> pd.Series:
    """
    Labels each row with its run's sample count, e.g. "96", or "96 (384 values)"
    when samples have several rows (one per FASTQ file). Only rows with a value
    are counted, so points stacked on one value still add to the count.
    """
    keys = ["project_name", *by]
    has_value = df[value_col].notna()
    samples = df["sample_name"].where(has_value).groupby([df[k] for k in keys])
    n_samples = samples.transform("nunique")
    n_values = samples.transform("count")
    return pd.Series(
        [
            f"{s}" if s == v else f"{s} ({v} values)"
            for s, v in zip(n_samples, n_values)
        ],
        index=df.index,
    )
