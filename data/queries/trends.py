import pandas as pd
from sqlmodel import Session, select

from data.models.reports import Assay, Run, Sample
from data.utils.formatting import format_categorical_columns


def get_trends_data(
    session: Session,
    assay_names: list[str],
    tool_model,
    metric_names: list[str],
    num_runs: int,
    sample_filter: str,
    color_by: str | None,
    symbol_by: str | None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Fetches data for the trends plot.
    Returns the DataFrame and a dictionary mapping 'color'/'symbol' to column names.
    """
    is_run_level = tool_model.metric_level == "run"

    columns_to_select = [Run.date, Run.run_folder]
    df_cols = ["date", "run_folder"]

    if not is_run_level:
        columns_to_select.append(Sample.name.label("sample_name"))
        df_cols.append("sample_name")

    for metric in metric_names:
        columns_to_select.append(getattr(tool_model, metric).label(metric))
        df_cols.append(metric)

    # Handle grouping columns
    grouping_args = {"color": None, "symbol": None}
    unique_group_vals = {val for val in [color_by, symbol_by] if val}

    for arg_val in unique_group_vals:
        model_name, field_name = arg_val.split(".")
        model = {"run": Run, "sample": Sample, "assay": Assay}.get(model_name)
        if model:
            unique_alias = f"{model_name}_{field_name}"
            columns_to_select.append(getattr(model, field_name).label(unique_alias))
            df_cols.append(unique_alias)

    if color_by:
        grouping_args["color"] = f"{color_by.split('.')[0]}_{color_by.split('.')[1]}"
    if symbol_by:
        grouping_args["symbol"] = f"{symbol_by.split('.')[0]}_{symbol_by.split('.')[1]}"

    # Build Query
    if is_run_level:
        statement = (
            select(*columns_to_select)
            .join(tool_model, Run.id == tool_model.run_id)
            .join(Assay, Run.assay_id == Assay.id)
            .where(Assay.name.in_(assay_names))
        )
        if num_runs:
            statement = statement.order_by(Run.date.desc()).limit(num_runs)
    else:
        statement = (
            select(*columns_to_select)
            .join(Sample, Run.id == Sample.run_id)
            .join(tool_model, Sample.id == tool_model.sample_id)
            .join(Assay, Run.assay_id == Assay.id)
            .where(Assay.name.in_(assay_names))
            .where(getattr(tool_model, metric_names[0]).is_not(None))
        )
        if sample_filter == "controls_only":
            statement = statement.where(Sample.is_control == True)
        if num_runs:
            run_ids_subquery = (
                statement.with_only_columns(Run.id)
                .distinct()
                .order_by(Run.date.desc())
                .limit(num_runs)
            )
            statement = statement.where(Run.id.in_(run_ids_subquery))

    results = session.exec(statement).all()
    if not results:
        return pd.DataFrame(columns=df_cols), grouping_args

    df = pd.DataFrame(results, columns=df_cols)
    df = df.sort_values("date", ascending=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    df = format_categorical_columns(df, color_by, symbol_by, grouping_args)

    return df, grouping_args
