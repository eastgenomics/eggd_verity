from sqlmodel import Session, select

from data.models.reports import Assay, Run, Sample


def get_runs_for_assay(
    session: Session, assay_name: str
) -> tuple[Assay | None, list[Run]]:
    """
    Fetches the assay object and all associated runs for a given assay name.
    """
    assay_obj = session.exec(select(Assay).where(Assay.name == assay_name)).first()
    if not assay_obj:
        return None, []

    runs = session.exec(select(Run).where(Run.assay_id == assay_obj.id)).all()
    return assay_obj, runs


def get_available_metrics_for_run(
    session: Session, run_id: int, model_map: dict
) -> list[str]:
    """
    Checks which metrics exist for a given run ID.
    """
    available_metrics = []
    for name, model in model_map.items():
        if model.metric_level == "run":
            exists_stmt = select(model.id).where(model.run_id == run_id).limit(1)
        else:
            exists_stmt = (
                select(model.id).join(Sample).where(Sample.run_id == run_id).limit(1)
            )

        if session.exec(exists_stmt).first():
            available_metrics.append(name)
    return available_metrics


def get_metric_data_for_run(session: Session, run_id: int, tool_model) -> list:
    """
    Fetches all metric records for a given run and tool model.
    """
    if tool_model.metric_level == "run":
        statement = select(tool_model).where(tool_model.run_id == run_id)
    else:
        statement = (
            select(Sample.name, tool_model)
            .join(tool_model)
            .where(Sample.run_id == run_id)
        )

    return session.exec(statement).all()
