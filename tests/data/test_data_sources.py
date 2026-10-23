"""Tests for finding and removing duplicate MultiQC reports."""

from datetime import datetime

import pandas as pd
from sqlmodel import Session, select

from data.manager.remove_data_source import remove_data_source
from data.models import Assay, MultiQCReport, Run, Sample
from data.models.samtools import SamtoolsFlagstat
from data.queries.warnings import get_plot_warnings
from tests.factories import add_report, run_identity


def _flagstat(sample: Sample, report: MultiQCReport) -> SamtoolsFlagstat:
    fields = {
        name: 0
        for name, field in SamtoolsFlagstat.model_fields.items()
        if field.is_required() and name not in {"id", "sample_id", "report_id"}
    }
    return SamtoolsFlagstat(sample_id=sample.id, report_id=report.id, **fields)


def _run_with_reports(session: Session, reports_samples: list[list[str]]) -> Run:
    """A run with one report per entry, each holding the named samples."""
    assay = session.exec(select(Assay)).first()
    if assay is None:
        assay = Assay(name="CEN38", ref_genome="GRCh38")
        session.add(assay)
        session.flush()
    run = Run(
        run_folder="261019_A01303_0876",
        date=datetime(2026, 10, 19),
        sequencer_id="A01303",
        assay_id=assay.id,
        **run_identity(),
    )
    session.add(run)
    session.flush()
    samples: dict[str, Sample] = {}
    for names in reports_samples:
        report = add_report(session, run)
        for name in names:
            if name not in samples:
                samples[name] = Sample(name=name, run_id=run.id)
                session.add(samples[name])
                session.flush()
            session.add(_flagstat(samples[name], report))
    session.commit()
    return run


def _plotted(*runs: Run) -> pd.DataFrame:
    return pd.DataFrame({"project_name": [r.project_name for r in runs]})


def test_rerun_report_is_flagged(session: Session):
    run = _run_with_reports(session, [["s1", "s2"], ["s1", "s2"]])

    warnings = get_plot_warnings(session, _plotted(run), SamtoolsFlagstat, None)

    assert len(warnings) == 1
    assert warnings[0]["level"] == "warning"
    assert run.project_name in warnings[0]["text"]
    assert "2 sample(s)" in warnings[0]["text"]
    for report in run.reports:
        assert report.file_id in warnings[0]["text"]


def test_old_split_reports_are_not_flagged(session: Session):
    run = _run_with_reports(session, [["s1", "s2"], ["s3"]])

    assert get_plot_warnings(session, _plotted(run), SamtoolsFlagstat, None) == []


def test_fewer_runs_than_requested_is_noted(session: Session):
    run = _run_with_reports(session, [["s1"]])

    warnings = get_plot_warnings(session, _plotted(run), SamtoolsFlagstat, 5)

    assert [w["level"] for w in warnings] == ["info"]
    assert "Only 1 run(s)" in warnings[0]["text"]


def test_dry_run_changes_nothing(session: Session):
    run = _run_with_reports(session, [["s1", "s2"], ["s1", "s2"]])
    rerun = run.reports[1]

    summary = remove_data_source(session, rerun.file_id, dry_run=True)

    assert summary.metric_rows == {"samtools_flagstat": 2}
    assert summary.samples == 0
    assert not summary.run_removed
    assert len(session.exec(select(SamtoolsFlagstat)).all()) == 4
    assert len(session.exec(select(MultiQCReport)).all()) == 2


def test_removing_a_rerun_keeps_the_run_and_shared_samples(session: Session):
    run = _run_with_reports(session, [["s1", "s2"], ["s1", "s2", "s3"]])
    original, rerun = run.reports

    remove_data_source(session, rerun.file_id, dry_run=False)

    assert [r.file_id for r in session.exec(select(MultiQCReport)).all()] == [
        original.file_id
    ]
    # s3 only had data from the removed report
    assert sorted(s.name for s in session.exec(select(Sample)).all()) == ["s1", "s2"]
    assert {r.report_id for r in session.exec(select(SamtoolsFlagstat)).all()} == {
        original.id
    }
    assert get_plot_warnings(session, _plotted(run), SamtoolsFlagstat, None) == []


def test_removing_the_last_report_removes_the_run(session: Session):
    run = _run_with_reports(session, [["s1"]])
    file_id = run.reports[0].file_id

    summary = remove_data_source(session, file_id, dry_run=False)

    assert summary.run_removed
    assert session.exec(select(Run)).all() == []
    assert session.exec(select(Sample)).all() == []


def test_unknown_file_id(session: Session):
    assert remove_data_source(session, f"file-{'9' * 24}") is None
