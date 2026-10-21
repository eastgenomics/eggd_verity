from datetime import datetime

import pytest
from sqlmodel import Session, select

from data.manager.clean_gen_stats import clean_gen_stats
from data.models.gen_stats import GenStats
from data.models.reports import Assay, Run, Sample
from data.queries.general import get_available_tools
from data.utils.model_utils import get_metric_models


def setup_test_runs(session: Session):
    """
    Sets up two assays and two runs:
    - Assay 'MYE' / Run 1: has custom metrics (some samples non-null, some null).
    - Assay 'CEN38' / Run 2: has GenStats records, but ALL custom metrics are null.
    """
    assay_mye = Assay(name="MYE", ref_genome="GRCh38")
    assay_cen = Assay(name="CEN38", ref_genome="GRCh38")
    session.add_all([assay_mye, assay_cen])
    session.commit()

    run_mye = Run(
        run_folder="RUN_MYE_001",
        date=datetime(2026, 1, 1),
        sequencer_id="A01303",
        source="project-111111111111111111111111:file-111111111111111111111111",
        assay_id=assay_mye.id,
    )
    run_cen = Run(
        run_folder="RUN_CEN_001",
        date=datetime(2026, 1, 1),
        sequencer_id="A01303",
        source="project-222222222222222222222222:file-222222222222222222222222",
        assay_id=assay_cen.id,
    )
    session.add_all([run_mye, run_cen])
    session.commit()

    # Samples for MYE run:
    sample_mye_1 = Sample(name="sample_mye_1", run_id=run_mye.id)
    sample_mye_2 = Sample(name="sample_mye_2", run_id=run_mye.id)
    # Samples for CEN run:
    sample_cen_1 = Sample(name="sample_cen_1", run_id=run_cen.id)
    sample_cen_2 = Sample(name="sample_cen_2", run_id=run_cen.id)

    session.add_all([sample_mye_1, sample_mye_2, sample_cen_1, sample_cen_2])
    session.commit()

    # GenStats for MYE: sample 1 has metrics, sample 2 is null
    gs_mye_1 = GenStats(sample_id=sample_mye_1.id, custom_coverage_250x=99.5)
    gs_mye_2 = GenStats(sample_id=sample_mye_2.id, custom_coverage_250x=None)

    # GenStats for CEN: all samples have all NULL metrics
    gs_cen_1 = GenStats(sample_id=sample_cen_1.id, custom_coverage_250x=None)
    gs_cen_2 = GenStats(sample_id=sample_cen_2.id, custom_coverage_250x=None)

    session.add_all([gs_mye_1, gs_mye_2, gs_cen_1, gs_cen_2])
    session.commit()

    return {
        "assay_mye": assay_mye,
        "assay_cen": assay_cen,
        "run_mye": run_mye,
        "run_cen": run_cen,
        "gs_mye_1": gs_mye_1,
        "gs_mye_2": gs_mye_2,
        "gs_cen_1": gs_cen_1,
        "gs_cen_2": gs_cen_2,
    }


def test_clean_gen_stats_dry_run(session: Session):
    data = setup_test_runs(session)

    # In dry run, it should detect 2 records from CEN to delete
    records_to_delete = clean_gen_stats(session, dry_run=True)
    assert records_to_delete == 2

    # Verify no records were deleted
    total_remaining = len(session.exec(select(GenStats)).all())
    assert total_remaining == 4


def test_clean_gen_stats_execution(session: Session):
    data = setup_test_runs(session)
    tool_map = get_metric_models()

    # Before clean: both MYE and CEN38 appear to have Gen Stats
    assert "Gen Stats" in get_available_tools(session, ["MYE"], tool_map)
    assert "Gen Stats" in get_available_tools(session, ["CEN38"], tool_map)

    # Execute cleanup
    deleted_count = clean_gen_stats(session, dry_run=False)
    assert deleted_count == 2

    # After clean: MYE still has Gen Stats, CEN38 no longer has Gen Stats
    assert "Gen Stats" in get_available_tools(session, ["MYE"], tool_map)
    assert "Gen Stats" not in get_available_tools(session, ["CEN38"], tool_map)

    # Check remaining records: both MYE records remain (including the null sample)
    remaining = session.exec(select(GenStats)).all()
    assert len(remaining) == 2
    assert {r.sample_id for r in remaining} == {
        data["gs_mye_1"].sample_id,
        data["gs_mye_2"].sample_id,
    }


def test_clean_gen_stats_empty_db(session: Session):
    assert clean_gen_stats(session, dry_run=False) == 0


def test_clean_gen_stats_all_valid(session: Session):
    assay = Assay(name="MYE", ref_genome="GRCh38")
    session.add(assay)
    session.commit()

    run = Run(
        run_folder="RUN_VALID_001",
        date=datetime(2026, 1, 1),
        sequencer_id="A01303",
        source="project-123456789012345678901234:file-123456789012345678901234",
        assay_id=assay.id,
    )
    session.add(run)
    session.commit()

    sample = Sample(name="sample_1", run_id=run.id)
    session.add(sample)
    session.commit()

    gs = GenStats(sample_id=sample.id, custom_coverage_500x=88.2)
    session.add(gs)
    session.commit()

    assert clean_gen_stats(session, dry_run=False) == 0
