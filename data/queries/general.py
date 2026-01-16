from sqlmodel import Session, select

from data.models.reports import Assay, Run, Sample


def get_assay_names(session: Session) -> list[str]:
    """
    Retrieves a sorted list of all unique assay names.
    """
    assays = session.exec(select(Assay.name).distinct()).all()
    return sorted(assays)


def get_available_tools(
    session: Session, assay_names: list[str], tool_map: dict
) -> list[str]:
    """
    Returns a list of tool names that have data for the given assays.
    """
    if not assay_names:
        return []

    available_tools = []

    for name, model in tool_map.items():
        # Check if any record exists for these assays using an EXISTS-like query
        if model.metric_level == "run":
            stmt = (
                select(model.id)
                .join(Run, model.run_id == Run.id)
                .join(Assay, Run.assay_id == Assay.id)
                .where(Assay.name.in_(assay_names))
                .limit(1)
            )
        else:
            stmt = (
                select(model.id)
                .join(Sample, model.sample_id == Sample.id)
                .join(Run, Sample.run_id == Run.id)
                .join(Assay, Run.assay_id == Assay.id)
                .where(Assay.name.in_(assay_names))
                .limit(1)
            )

        if session.exec(stmt).first():
            available_tools.append(name)

    return sorted(available_tools)
