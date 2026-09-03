from sqlalchemy import distinct, func
from sqlmodel import Session, select

from data.models.reports import Assay, Run, Sample


def get_summary_stats(
    session: Session, include_legacy: bool = False
) -> tuple[list, list, list, list]:
    """
    Fetches summary statistics for the dashboard.
    Returns:
        - summary_results: List of tuples (Assay, Runs, Samples, MinDate, MaxDate)
        - sequencer_results: List of tuples (Assay, Sequencer, RunCount)
        - total_sequencer_results: List of tuples (Sequencer, RunCount)
        - sex_results: List of tuples (Assay, Sex, SampleCount)
    """
    assay_filter = Assay.active.is_(True) if not include_legacy else None

    # 1. General Summary
    summary_stmt = (
        select(
            Assay.name,
            func.count(distinct(Run.run_folder)).label("run_count"),
            func.count(distinct(Sample.name)).label("sample_count"),
            func.min(Run.date).label("min_date"),
            func.max(Run.date).label("max_date"),
        )
        .select_from(Assay)
        .outerjoin(Run, Assay.id == Run.assay_id)
        .outerjoin(Sample, Run.id == Sample.run_id)
    )
    if assay_filter is not None:
        summary_stmt = summary_stmt.where(assay_filter)
    summary_stmt = summary_stmt.group_by(Assay.name).order_by(Assay.name)
    summary_results = session.exec(summary_stmt).all()

    # 2. Sequencer per Assay
    sequencer_stmt = select(
        Assay.name,
        Run.sequencer_id,
        func.count(distinct(Run.run_folder)).label("run_count"),
    ).join(Assay, Run.assay_id == Assay.id)
    if assay_filter is not None:
        sequencer_stmt = sequencer_stmt.where(assay_filter)
    sequencer_stmt = sequencer_stmt.group_by(Assay.name, Run.sequencer_id)
    sequencer_results = session.exec(sequencer_stmt).all()

    # 3. Total Sequencer Usage
    total_sequencer_stmt = (
        select(
            Run.sequencer_id,
            func.count(distinct(Run.run_folder)).label("run_count"),
        )
        .join(Assay, Run.assay_id == Assay.id)
        .group_by(Run.sequencer_id)
    )
    if assay_filter is not None:
        total_sequencer_stmt = total_sequencer_stmt.where(assay_filter)
    total_sequencer_results = session.exec(total_sequencer_stmt).all()

    # 4. Sex Distribution
    sex_stmt = (
        select(
            Assay.name,
            Sample.sex,
            func.count(distinct(Sample.name)).label("sample_count"),
        )
        .join(Run, Assay.id == Run.assay_id)
        .join(Sample, Run.id == Sample.run_id)
    )
    if assay_filter is not None:
        sex_stmt = sex_stmt.where(assay_filter)
    sex_stmt = sex_stmt.group_by(Assay.name, Sample.sex)
    sex_results = session.exec(sex_stmt).all()

    return summary_results, sequencer_results, total_sequencer_results, sex_results
