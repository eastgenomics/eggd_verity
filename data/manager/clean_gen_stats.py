"""Database cleanup script to remove GenStats records associated with runs that have no custom metrics."""

from typing import List
import fire
from sqlalchemy import delete
from sqlmodel import Session, col, create_engine, func, or_, select

from data.config import DATABASE_PATH
from data.models import Assay, Run, Sample
from data.models.gen_stats import GenStats


def clean_gen_stats(session: Session, dry_run: bool = True) -> int:
    """
    Finds sequencing runs associated with GenStats records that contain no custom
    metrics (all custom coverage fields are NULL for every sample in the run)
    and removes those GenStats records.

    Args:
        session: Active SQLModel/SQLAlchemy session.
        dry_run: When True, simulates the cleanup without committing changes.

    Returns:
        The total number of GenStats records removed (or to be removed).
    """
    metric_fields = [
        GenStats.custom_coverage_250x,
        GenStats.custom_coverage_500x,
        GenStats.custom_coverage_1000x,
        GenStats.custom_coverage_usable_unique_bases_on_target,
    ]
    has_metrics_cond = or_(*(f.is_not(None) for f in metric_fields))

    # Find run IDs that have at least one GenStats record with custom metrics
    runs_with_metrics_stmt = (
        select(Run.id)
        .join(Sample, Sample.run_id == Run.id)
        .join(GenStats, GenStats.sample_id == Sample.id)
        .where(has_metrics_cond)
        .distinct()
    )
    runs_with_metrics = set(session.exec(runs_with_metrics_stmt).all())

    # Get all runs that currently have GenStats records
    all_gen_stats_runs_stmt = (
        select(Run.id, Run.run_folder, Assay.name, func.count(GenStats.id))
        .join(Sample, Sample.run_id == Run.id)
        .join(GenStats, GenStats.sample_id == Sample.id)
        .join(Assay, Assay.id == Run.assay_id)
        .group_by(Run.id, Run.run_folder, Assay.name)
    )
    all_runs = session.exec(all_gen_stats_runs_stmt).all()

    if not all_runs:
        print("No GenStats records found in the database.")
        return 0

    runs_to_delete = []
    total_records_to_delete = 0

    for run_id, run_folder, assay_name, count in all_runs:
        if run_id in runs_with_metrics:
            print(
                f"[KEEP] Run {run_id} ({assay_name} - {run_folder}): "
                f"{count} records (contains custom metrics)"
            )
        else:
            print(
                f"[DELETE] Run {run_id} ({assay_name} - {run_folder}): "
                f"{count} records (no custom metrics)"
            )
            runs_to_delete.append(run_id)
            total_records_to_delete += count

    if not runs_to_delete:
        print(
            "\nAll runs with GenStats records contain valid custom metrics. No cleanup required."
        )
        return 0

    if dry_run:
        print(
            f"\n[DRY RUN COMPLETE] Found {len(runs_to_delete)} run(s) without custom metrics."
        )
        print(f"{total_records_to_delete} GenStats record(s) would be deleted.")
        print("No changes were committed to the database.")
    else:
        try:
            sample_subquery = select(Sample.id).where(
                col(Sample.run_id).in_(runs_to_delete)
            )
            del_stmt = delete(GenStats).where(
                col(GenStats.sample_id).in_(sample_subquery)
            )
            res = session.exec(del_stmt)
            session.commit()
            print(
                f"\n[SUCCESS] Deleted {res.rowcount} GenStats record(s) across "
                f"{len(runs_to_delete)} run(s)."
            )
        except Exception:
            session.rollback()
            raise

    return total_records_to_delete


def main(dry_run: bool = True) -> None:
    engine = create_engine(f"sqlite:///{DATABASE_PATH}")
    with Session(engine) as session:
        clean_gen_stats(session, dry_run=dry_run)


if __name__ == "__main__":
    fire.Fire(main)
