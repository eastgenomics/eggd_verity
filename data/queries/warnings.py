"""Checks behind the warning box shown above the plots."""

import pandas as pd
from sqlmodel import Session, select

from data.models import MultiQCReport, Run

REMOVE_COMMAND = "python -m data.manager.remove_data_source"


def get_plot_warnings(
    session: Session,
    df: pd.DataFrame,
    tool_model,
    num_runs: int | None,
) -> list[dict[str, str]]:
    """
    Returns warnings about the plotted data as {"level", "text"} dicts, where level
    is a Bootstrap colour ("warning", "info"). Empty when there is nothing to say.
    """
    if df.empty:
        return []

    project_names = list(df["project_name"].unique())
    warnings = find_duplicate_reports(session, project_names, tool_model)

    if getattr(tool_model, "per_fastq", False) and "sample_name" in df.columns:
        rows_per_sample = df.groupby(["project_name", "sample_name"]).size()
        low, high = rows_per_sample.min(), rows_per_sample.max()
        if high > 1:
            per_sample = f"{low}" if low == high else f"{low} to {high}"
            warnings.append(
                {
                    "level": "info",
                    "text": (
                        f"{tool_model.display_name} values are per FASTQ file "
                        f"(lane and read pair), so each sample has {per_sample} "
                        "points. See the Explore page for each file's values."
                    ),
                }
            )

    if num_runs and len(project_names) < num_runs:
        warnings.append(
            {
                "level": "info",
                "text": (
                    f"Only {len(project_names)} run(s) have {tool_model.display_name} "
                    f"data for the selected assay(s); {num_runs} were requested."
                ),
            }
        )
    return warnings


def find_duplicate_reports(
    session: Session, project_names: list[str], tool_model
) -> list[dict[str, str]]:
    """
    Finds runs where the same data was loaded from more than one MultiQC report,
    which happens when a pipeline is rerun. For sample level tools that is a sample
    with rows from several reports; old projects whose reports hold different
    samples are not flagged. For run level tools it is any run with several reports.
    """
    is_run_level = tool_model.metric_level == "run"
    key = tool_model.run_id if is_run_level else tool_model.sample_id

    statement = (
        select(Run.project_name, MultiQCReport.file_id, key.label("key"))
        .join(MultiQCReport, MultiQCReport.id == tool_model.report_id)
        .join(Run, Run.id == MultiQCReport.run_id)
        .where(Run.project_name.in_(project_names))
        .distinct()
    )
    rows = pd.DataFrame(
        session.exec(statement).all(), columns=["project_name", "file_id", "key"]
    )
    if rows.empty:
        return []

    reports_per_key = rows.groupby(["project_name", "key"])["file_id"].nunique()
    duplicated = reports_per_key[reports_per_key > 1].reset_index()

    warnings = []
    for project_name in duplicated["project_name"].unique():
        dup_keys = duplicated.loc[duplicated["project_name"] == project_name, "key"]
        file_ids = sorted(
            rows.loc[
                (rows["project_name"] == project_name) & rows["key"].isin(dup_keys),
                "file_id",
            ].unique()
        )
        what = "run" if is_run_level else f"{len(dup_keys)} sample(s)"
        warnings.append(
            {
                "level": "warning",
                "text": (
                    f"{project_name}: {what} have {tool_model.display_name} data from "
                    f"{len(file_ids)} MultiQC reports ({', '.join(file_ids)}), so "
                    f"values are counted more than once. Check which report to keep "
                    f"and remove the other with `{REMOVE_COMMAND} <file-id>`."
                ),
            }
        )
    return warnings
