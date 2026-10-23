"""ETL Pipeline for MultiQC Data into Relational Database"""
import logging
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, Type

import dxpy
import fire
import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

from data.models import Assay, BaseMetrics, MultiQCReport, Run
from data.utils.dnanexus import login_to_dnanexus, find_dx_projects, get_multiqc_reports, get_project_metadata
from data.utils.multiqc import parse_multiqc_section, read_multiqc_data
from data.utils.sample import get_or_create_run_samples

from .config import IGNORE_SECTIONS, LOGGING_CONFIG, MAX_WORKERS, PROD_PROJECT_PATTERN
from .db_init import create_db_and_tables, engine

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def get_or_create(
    session: Session,
    model: Type[SQLModel],
    defaults: Dict[str, Any] | None = None,
    **kwargs,
) -> SQLModel:
    """
    Fetches an object from the database or creates it if it doesn't exist.
    NB: The caller is responsible for committing the session.
    """
    try:
        query = select(model)
        for key, value in kwargs.items():
            query = query.where(getattr(model, key) == value)

        instance = session.exec(query).first()
        if instance:
            return instance
        else:
            create_kwargs = {**kwargs, **(defaults or {})}
            instance = model(**create_kwargs)
            session.add(instance)
            session.flush()  # Flush to get the ID for relationships without committing
            session.refresh(instance)
            return instance

    except IntegrityError as e:
        # SQLite and Postgres word unique violations differently
        if "UNIQUE constraint failed" in str(e) or "duplicate key value" in str(e):
            # Race condition: another thread created the same object
            session.rollback()
            # Blow up if not exactly one match
            return session.exec(query).one()
        else:
            # Re-raise other integrity errors (foreign key, not null, etc.)
            raise


def get_mqc_to_models() -> dict[str, Type[BaseMetrics]]:
    """Returns a mapping of MultiQC section names to SQLModel."""
    model_map = {}

    for model_cls in BaseMetrics.__subclasses__():
        if (
            not hasattr(model_cls, "multiqc_section_names")
            or not model_cls.multiqc_section_names
        ):
            logging.warning(
                f"'{model_cls.__name__}' is not mapped to a MultiQC section"
            )
            continue

        for section_name in model_cls.multiqc_section_names:
            if section_name in model_map:
                # This shouldn't happen but shout if it does
                logging.warning(
                    f"Duplicate MultiQC section '{section_name}' found. Overwriting."
                )
            model_map[section_name] = model_cls
    return model_map


def process_report(
    project_id: str, file_id: str, model_map: dict[str, Type[BaseMetrics]]
) -> None:
    """
    End-to-end processing for a single MultiQC report.
    Extracts, transforms, and loads multiqc data into the database transactionally.
    """
    source = f"{project_id}:{file_id}"
    logging.info(f"Starting processing for file: {source}")

    try:
        with Session(engine) as session:
            report = session.exec(
                select(MultiQCReport).where(MultiQCReport.file_id == file_id)
            ).first()
            if report and report.processed_at:
                logging.info(f"Skipping {source}, already processed.")
                return

        metadata = get_project_metadata(project_id, file_id)
        run_folder = metadata["run_folder"]
        project_name = metadata["project_name"]

        multiqc_data = read_multiqc_data(project_id, file_id)

        with Session(engine) as session:
            # Get or Create Assay, Run and Report Objects
            assay = get_or_create(
                session,
                Assay,
                name=metadata["assay"],
                ref_genome=metadata["ref_genome"],
            )

            run_defaults = {
                "project_name": project_name,
                "run_folder": run_folder,
                "date": metadata["date"],
                "sequencer_id": metadata["sequencer_id"],
                "assay_id": assay.id,
            }
            run = get_or_create(
                session, Run, project_id=project_id, defaults=run_defaults
            )
            report = get_or_create(
                session, MultiQCReport, file_id=file_id, defaults={"run_id": run.id}
            )

            sample_map = get_or_create_run_samples(
                session=session,
                multiqc_data=multiqc_data,
                run_id=run.id,
            )
            logging.info(
                f"Identified {len(sample_map)} samples for run {project_name}"
            )

            for section_name, section_data in multiqc_data.items():
                model = model_map.get(section_name)
                if not model:
                    if section_name not in IGNORE_SECTIONS:
                        logger.warning(f"No model for section: '{section_name}'")
                    continue

                df = parse_multiqc_section(section_data)
                if df.empty:
                    logger.warning(f"Empty df for {section_name} in {source}")
                    continue

                logger.info(f"creating records for {section_name}")

                recs = model.bulk_create_from_df(
                    session=session,
                    df=df,
                    run=run,
                    report=report,
                    sample_map=sample_map,
                )
                logging.debug(f"Added {recs} records for {section_name}")

            report.processed_at = datetime.now(timezone.utc)
            session.commit()
            logging.info(
                f"Successfully processed and committed records in {source}"
            )

    except Exception as e:
        logger.error(f"Failed to process {source}: {e}", exc_info=True)


def process_project_reports(
    project_id: str, file_ids: list[str], model_map: dict[str, Type[BaseMetrics]]
) -> None:
    """
    Processes a project's reports one after another. Reports of one project share
    the Run and its samples, so loading them in parallel would race to create them.
    """
    for file_id in file_ids:
        process_report(project_id, file_id, model_map)


def main(
    *project_ids: str,
    created_after: str | None = None,
    created_before: str | None = None,
    sample_size: int | None = None,
) -> None:
    """
    Runs the main ETL pipeline for processing MultiQC data into a relational database.

    Args:
        *project_ids (str): A variable number of project IDs to process. If none are
            provided, the pipeline will search for projects based on other criteria.
        created_after (str, optional):
            Relative time string for project search (e.g., "-5d", "-2w", "-1h").
        created_before (str, optional):
            Relative time string for project search (e.g., "-5d", "-2w", "-1h").
        sample_size (int, optional):
            Randomly sample a number of projects to process.

    """
    create_db_and_tables()
    model_map = get_mqc_to_models()

    login_to_dnanexus()

    if not project_ids:
        logger.info(
            "No project IDs provided via command line, searching for projects..."
        )
        project_ids = find_dx_projects(
            pattern=PROD_PROJECT_PATTERN,
            created_after=created_after,
            created_before=created_before,
        )

    if not project_ids:
        logger.warning("No projects found to process. Exiting.")
        return

    if sample_size and len(project_ids) > sample_size:
        logger.info(f"Randomly sampling {sample_size} projects.")
        project_ids = random.sample(project_ids, sample_size)

    df = get_multiqc_reports(list(project_ids))

    if df is None or df.empty:
        logger.warning("No live MultiQC reports found. Exiting.")
        return

    logger.info(f"Starting ETL pipeline for {len(df)} MultiQC reports...")
    reports_by_project = df.groupby("project_id", sort=False)["file_id"].apply(list)
    n_workers = min(MAX_WORKERS, len(reports_by_project))
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [
            executor.submit(process_project_reports, project_id, file_ids, model_map)
            for project_id, file_ids in reports_by_project.items()
        ]
        for future in as_completed(futures):
            future.result()

    logger.info("Pipeline execution complete.")


if __name__ == "__main__":
    fire.Fire(main)
