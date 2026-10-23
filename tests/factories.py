"""Helpers for building test data that satisfies the run and report constraints."""

from itertools import count

from sqlmodel import Session

from data.models import MultiQCReport, Run

_ids = count(1)


def run_identity(run_folder: str = "run") -> dict[str, str]:
    """Unique project_id and project_name fields for a Run."""
    n = next(_ids)
    return {"project_id": f"project-{n:024d}", "project_name": f"002_{run_folder}_{n}"}


def add_report(session: Session, run: Run) -> MultiQCReport:
    """Adds a MultiQC report to a run and flushes it, so it has an id."""
    report = MultiQCReport(file_id=f"file-{next(_ids):024d}", run_id=run.id)
    session.add(report)
    session.flush()
    return report
