import pandas as pd
from sqlmodel import Session, select

from data.models.reports import Assay, Run, Sample
from data.utils.formatting import format_categorical_columns


def get_correlation_data(
    session: Session,
    assay_names: list[str],
    run_folders: list[str],
    x_model,
    x_metric: str,
    y_model,
    y_metric: str,
    sample_filter: str,
    color_by: str | None,
    symbol_by: str | None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Fetches data for the correlation plot.
    """
    cols_to_select = []
    df_cols = []
    grouping_args = {"color": None, "symbol": None}

    # Metrics
    if x_model == y_model:
        cols_to_select.extend(
            [
                getattr(x_model, x_metric).label("x"),
                getattr(x_model, y_metric).label("y"),
            ]
        )
    else:
        cols_to_select.extend(
            [
                getattr(x_model, x_metric).label("x"),
                getattr(y_model, y_metric).label("y"),
            ]
        )
    df_cols.extend(["x", "y"])

    # Grouping
    unique_group_vals = {val for val in [color_by, symbol_by] if val}
    for arg_val in unique_group_vals:
        model_name, field_name = arg_val.split(".")
        model = {"run": Run, "sample": Sample, "assay": Assay}.get(model_name)
        if model:
            unique_alias = f"{model_name}_{field_name}"
            cols_to_select.append(getattr(model, field_name).label(unique_alias))
            df_cols.append(unique_alias)

    if color_by:
        grouping_args["color"] = f"{color_by.split('.')[0]}_{color_by.split('.')[1]}"
    if symbol_by:
        grouping_args["symbol"] = f"{symbol_by.split('.')[0]}_{symbol_by.split('.')[1]}"

    # Metadata
    cols_to_select.extend(
        [Sample.name.label("sample_name"), Run.run_folder.label("run_folder")]
    )
    df_cols.extend(["sample_name", "run_folder"])

    # Query
    stmt = select(*cols_to_select).select_from(Sample)
    stmt = stmt.join(Run, Sample.run_id == Run.id).join(Assay, Run.assay_id == Assay.id)
    stmt = stmt.join(x_model, Sample.id == x_model.sample_id)
    if x_model != y_model:
        stmt = stmt.join(y_model, Sample.id == y_model.sample_id)

    stmt = stmt.where(Assay.name.in_(assay_names))
    if run_folders:
        stmt = stmt.where(Run.run_folder.in_(run_folders))
    if sample_filter == "controls_only":
        stmt = stmt.where(Sample.is_control == True)

    results = session.exec(stmt).all()
    df = pd.DataFrame(results, columns=df_cols).dropna(subset=["x", "y"])
    df = format_categorical_columns(df, color_by, symbol_by, grouping_args)

    return df, grouping_args
