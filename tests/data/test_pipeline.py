"""Tests for loading MultiQC reports: one Run per project, one row per report."""

from datetime import datetime
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from data.models import MultiQCReport, Run, Sample
from data.models.samtools import SamtoolsFlagstat

pipeline = pytest.importorskip("data.pipeline")

PROJECT_ID = f"project-{'a' * 24}"
FILE_ORIGINAL = f"file-{'1' * 24}"
FILE_RERUN = f"file-{'2' * 24}"


def _flagstat_section(samples: list[str]) -> dict:
    fields = {
        name: 0
        for name, field in SamtoolsFlagstat.model_fields.items()
        if field.is_required() and name not in {"id", "sample_id", "report_id"}
    }
    return {name: dict(fields, mapped_passed=100) for name in samples}


def _multiqc(samples: list[str]) -> dict:
    return {
        "multiqc_fastqc": {
            f"{s}_S{i}_L001_R1": {"total_sequences": 10}
            for i, s in enumerate(samples, 1)
        },
        "multiqc_samtools_flagstat": _flagstat_section(samples),
    }


METADATA = {
    "project_name": "002_261019_A01303_0876_AHWMJMDRX7_38_CEN",
    "run_folder": "261019_A01303_0876_AHWMJMDRX7_38",
    "date": datetime(2026, 10, 19),
    "sequencer_id": "A01303",
    "assay": "CEN38",
    "ref_genome": "GRCh38",
}


@pytest.fixture
def load(session: Session):
    """Runs process_report against the test database with stubbed DNAnexus calls."""
    # FastQC is only needed here to create the run samples
    model_map = {"multiqc_samtools_flagstat": SamtoolsFlagstat}

    def _load(file_id: str, samples: list[str]):
        with (
            patch.object(pipeline, "engine", session.get_bind()),
            patch.object(pipeline, "get_project_metadata", return_value=METADATA),
            patch.object(pipeline, "read_multiqc_data", return_value=_multiqc(samples)),
        ):
            pipeline.process_report(PROJECT_ID, file_id, model_map)
        session.expire_all()

    return _load


def test_reports_of_one_project_share_the_run_and_samples(session, load):
    load(FILE_ORIGINAL, ["s1", "s2"])
    load(FILE_RERUN, ["s1", "s2"])

    runs = session.exec(select(Run)).all()
    assert [(r.project_id, r.project_name) for r in runs] == [
        (PROJECT_ID, METADATA["project_name"])
    ]
    reports = session.exec(select(MultiQCReport)).all()
    assert {r.file_id for r in reports} == {FILE_ORIGINAL, FILE_RERUN}
    assert all(r.processed_at for r in reports)
    assert len(session.exec(select(Sample)).all()) == 2
    # The rerun's rows are kept apart by report, ready to be found and removed
    rows = session.exec(select(SamtoolsFlagstat)).all()
    assert sorted(r.report_id for r in rows) == sorted(
        [reports[0].id] * 2 + [reports[1].id] * 2
    )


def test_processed_report_is_skipped(session, load):
    load(FILE_ORIGINAL, ["s1"])
    with (
        patch.object(pipeline, "engine", session.get_bind()),
        patch.object(pipeline, "get_project_metadata", return_value=METADATA),
        patch.object(pipeline, "read_multiqc_data") as read,
    ):
        pipeline.process_report(PROJECT_ID, FILE_ORIGINAL, {})
    read.assert_not_called()
    assert len(session.exec(select(SamtoolsFlagstat)).all()) == 1
