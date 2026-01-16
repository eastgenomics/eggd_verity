from sqlalchemy import distinct, func
from sqlmodel import Session, select

from data.models.reports import Assay, Run, Sample


def get_summary_stats(session: Session) -> tuple[list, list, list, list]:
    """
    Fetches summary statistics for the home page.
    Returns:
        - summary_results: List of tuples (Assay, Runs, Samples, MinDate, MaxDate)
        - sequencer_results: List of tuples (Assay, Sequencer, RunCount)
        - total_sequencer_results: List of tuples (Sequencer, RunCount)
        - sex_results: List of tuples (Assay, Sex, SampleCount)
    """
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
        .group_by(Assay.name)
        .order_by(Assay.name)
    )
    summary_results = session.exec(summary_stmt).all()

    # 2. Sequencer per Assay
    sequencer_stmt = (
        select(
            Assay.name,
            Run.sequencer_id,
            func.count(distinct(Run.run_folder)).label("run_count"),
        )
        .join(Assay, Run.assay_id == Assay.id)
        .group_by(Assay.name, Run.sequencer_id)
    )
    sequencer_results = session.exec(sequencer_stmt).all()

    # 3. Total Sequencer Usage
    total_sequencer_stmt = select(
        Run.sequencer_id, func.count(distinct(Run.run_folder)).label("run_count")
    ).group_by(Run.sequencer_id)
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
        .group_by(Assay.name, Sample.sex)
    )
    sex_results = session.exec(sex_stmt).all()

    return summary_results, sequencer_results, total_sequencer_results, sex_results
