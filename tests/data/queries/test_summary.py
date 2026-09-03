from datetime import datetime

from data.models.reports import Assay, Run, Sample
from data.queries.summary import get_summary_stats


def add_assay_run_sample(session, assay):
    session.add(assay)
    session.flush()
    run = Run(
        run_folder=f"run-{assay.name}",
        date=datetime(2025, 1, 1),
        sequencer_id="SEQ1",
        source=("project-123456789012345678901234:" f"file-{assay.id:024d}"),
        assay_id=assay.id,
    )
    session.add(run)
    session.flush()
    session.add(Sample(name=f"sample-{assay.name}", run_id=run.id))
    session.commit()


def test_summary_stats_excludes_inactive_assays_by_default(session):
    add_assay_run_sample(session, Assay(name="ACTIVE", active=True))
    add_assay_run_sample(session, Assay(name="LEGACY", active=False))

    summary, by_assay, total, sex = get_summary_stats(session)

    assert [row[0] for row in summary] == ["ACTIVE"]
    assert [row[0] for row in by_assay] == ["ACTIVE"]
    assert total == [("SEQ1", 1)]
    assert [row[0] for row in sex] == ["ACTIVE"]


def test_summary_stats_can_include_inactive_assays(session):
    add_assay_run_sample(session, Assay(name="ACTIVE", active=True))
    add_assay_run_sample(session, Assay(name="LEGACY", active=False))

    summary, by_assay, total, sex = get_summary_stats(session, include_legacy=True)

    assert {row[0] for row in summary} == {"ACTIVE", "LEGACY"}
    assert {row[0] for row in by_assay} == {"ACTIVE", "LEGACY"}
    assert total == [("SEQ1", 2)]
    assert {row[0] for row in sex} == {"ACTIVE", "LEGACY"}


def test_assay_defaults_to_active():
    assert Assay(name="NEW_ASSAY").active is True
