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
