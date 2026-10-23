"""
Removes one MultiQC report (data source) and the data loaded from it.

Use it when a pipeline rerun left two reports in one DNAnexus project and one of
them is unwanted. The plot pages warn about these and give the file ID.

    python -m data.manager.remove_data_source file-xxxx                  # dry run
    python -m data.manager.remove_data_source file-xxxx --dry_run=False  # delete

Removed in order: the report's metric rows, samples left with no metric rows from
any other report, the report itself, and the run if it has no other reports.
"""

from dataclasses import dataclass, field

import fire
from sqlalchemy import delete, func
from sqlmodel import Session, select

from data.database import get_engine
from data.models import BaseMetrics, MultiQCReport, Run, Sample


@dataclass
class RemovalSummary:
    file_id: str
    project_name: str
    metric_rows: dict[str, int] = field(default_factory=dict)
    samples: int = 0
    run_removed: bool = False


def _metric_models() -> list[type[BaseMetrics]]:
    return sorted(BaseMetrics.__subclasses__(), key=lambda m: m.__tablename__)


def _is_sample_level(model: type[BaseMetrics]) -> bool:
    return model.metric_level == "sample"


def remove_data_source(
    session: Session, file_id: str, dry_run: bool = True
) -> RemovalSummary | None:
    """
    Removes the report with the given DNAnexus file ID. Returns what was (or, on a
    dry run, would be) removed, or None if no such report exists.
    """
    report = session.exec(
        select(MultiQCReport).where(MultiQCReport.file_id == file_id)
    ).first()
    if report is None:
        print(f"[NOT FOUND] No MultiQC report with file ID {file_id}")
        return None

    run = session.get(Run, report.run_id)
    summary = RemovalSummary(file_id=file_id, project_name=run.project_name)

    run_sample_ids = set(
        session.exec(select(Sample.id).where(Sample.run_id == run.id)).all()
    )
    kept_sample_ids: set[int] = set()

    for model in _metric_models():
        count = session.exec(
            select(func.count()).select_from(model).where(model.report_id == report.id)
        ).one()
        if count:
            summary.metric_rows[model.__tablename__] = count
        if _is_sample_level(model) and run_sample_ids:
            kept_sample_ids.update(
                session.exec(
                    select(model.sample_id)
                    .where(model.sample_id.in_(run_sample_ids))
                    .where(model.report_id != report.id)
                    .distinct()
                ).all()
            )

    orphan_sample_ids = run_sample_ids - kept_sample_ids
    summary.samples = len(orphan_sample_ids)
    other_reports = session.exec(
        select(func.count())
        .select_from(MultiQCReport)
        .where(MultiQCReport.run_id == run.id, MultiQCReport.id != report.id)
    ).one()
    summary.run_removed = other_reports == 0

    _print_summary(summary, dry_run)
    if dry_run:
        return summary

    try:
        for model in _metric_models():
            session.exec(delete(model).where(model.report_id == report.id))
        if orphan_sample_ids:
            session.exec(delete(Sample).where(Sample.id.in_(orphan_sample_ids)))
        session.exec(delete(MultiQCReport).where(MultiQCReport.id == report.id))
        if summary.run_removed:
            session.exec(delete(Run).where(Run.id == run.id))
        session.commit()
    except Exception:
        session.rollback()
        raise
    return summary


def _print_summary(summary: RemovalSummary, dry_run: bool) -> None:
    verb = "Would remove" if dry_run else "Removing"
    print(f"{verb} report {summary.file_id} from {summary.project_name}:")
    for table, count in summary.metric_rows.items():
        print(f"  {count:>6} rows from {table}")
    print(f"  {summary.samples:>6} samples with no data from other reports")
    if summary.run_removed:
        print("  the run itself (it has no other reports)")
    if dry_run:
        print("[DRY RUN COMPLETE] Nothing was changed. Add --dry_run=False to delete.")


def main(*file_ids: str, dry_run: bool = True) -> None:
    if not file_ids:
        raise SystemExit("Give at least one DNAnexus file ID (file-...)")
    with Session(get_engine()) as session:
        for file_id in file_ids:
            remove_data_source(session, file_id, dry_run=dry_run)


if __name__ == "__main__":
    fire.Fire(main)
