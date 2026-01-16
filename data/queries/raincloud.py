import pandas as pd
from sqlmodel import Session, select

from data.models.reports import Assay, Run, Sample
from data.utils.formatting import format_categorical_columns


def get_raincloud_data(
    session: Session,
    assay_names: list[str],
    tool_model,
    metric_name: str,
    num_runs: int,
    color_by: str | None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Fetches data for the raincloud plot.
    """
    is_run_level = tool_model.metric_level == "run"

    columns_to_select = [
        Run.date,
        Run.run_folder.label("run_folder"),
        getattr(tool_model, metric_name).label(metric_name),
    ]
    df_cols = ["date", "run_folder", metric_name]

    if not is_run_level:
        columns_to_select.append(Sample.name.label("sample_name"))
        df_cols.append("sample_name")

    grouping_args = {"color": None}
    if color_by:
        model_name, field_name = color_by.split(".")
        model = {"run": Run, "sample": Sample, "assay": Assay}.get(model_name)
        if model:
            unique_alias = f"{model_name}_{field_name}"
            columns_to_select.append(getattr(model, field_name).label(unique_alias))
            df_cols.append(unique_alias)
            grouping_args["color"] = unique_alias

    # Subquery for latest runs
    latest_runs_stmt = (
        select(Run.id)
        .join(Assay, Run.assay_id == Assay.id)
        .where(Assay.name.in_(assay_names))
        .order_by(Run.date.desc())
        .limit(num_runs)
    ).alias("latest_runs")

    if is_run_level:
        statement = select(*columns_to_select).join(
            tool_model, Run.id == tool_model.run_id
        )
    else:
        statement = (
            select(*columns_to_select)
            .join(Sample, Run.id == Sample.run_id)
            .join(tool_model, Sample.id == tool_model.sample_id)
        )

    statement = statement.join(Assay, Run.assay_id == Assay.id).join(
        latest_runs_stmt, Run.id == latest_runs_stmt.c.id
    )

    results = session.exec(statement).all()
    if not results:
        return pd.DataFrame(columns=df_cols), grouping_args

    df = pd.DataFrame(results, columns=df_cols)
    df = df.sort_values("date", ascending=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    if is_run_level:
        df["sample_name"] = df["run_folder"]

    df = format_categorical_columns(df, color_by, None, grouping_args)
    return df, grouping_args
