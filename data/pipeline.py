import json
import logging
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

import dxpy
import fire
import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

from data.models import (
    bcl2fastq,
    bclconvert,
    fastqc,
    happy,
    interop,
    picard,
    rna_seqc,
    samtools,
    sentieon,
    sex_check,
    somalier,
    sompy,
    tso500,
    vcfqc,
    verifybamid,
)
from data.models.choices import SexKaryotype
from data.models.reports import Assay, BaseMetrics, Run, Sample

from .config import IGNORE_SECTIONS, LOGGING_CONFIG, MAX_WORKERS, PROD_PROJECT_PATTERN
from .db_init import create_db_and_tables, engine
from .utils import clean_df, find_dx_projects, get_multiqc_reports, get_project_metadata

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
        if "UNIQUE constraint failed" in str(e):
            # Race condition: another thread created the same object
            session.rollback()
            # Blow up if not exactly one match
            return session.exec(query).one()
        else:
            # Re-raise other integrity errors (foreign key, not null, etc.)
            raise


def get_or_create_sample(session: Session, name: str, run_id: int) -> Sample:
    """Special get_or_create for Sample, handling control and sex logic."""

    # Remove any trailing run suffixes
    name = re.sub(r"_S\d+.*$", "", name)

    control_pattern = r"-[0-9]+Q[0-9]+-|NA\d+.*|HG00.*"
    is_control = bool(re.search(control_pattern, name))

    batch = ""
    testcode = None
    sex = SexKaryotype.UNKNOWN

    parts = name.split("-")

    # Extract batch, testcode, and sex from sample name

    # Case 1: Handle HRD naming convention (...-25-HRDS11-9197-F)
    if len(parts) >= 7 and "HRD" in parts[-3]:
        sex = SexKaryotype(parts[-1])
        testcode = parts[-2]
        batch = parts[-3]

    # Case 2: Handle standard naming convention (...-BATCH-TESTCODE-SEX-...)
    elif len(parts) >= 6:
        sex = SexKaryotype(parts[-2])
        testcode = parts[-3]
        batch = parts[-4]

    # Case 3: Handle naming convention for Helios (...-BATCH-TESTCODE)
    elif len(parts) >= 4:
        if parts[-1].isdigit() and len(parts[-1]) >= 4:
            testcode = parts[-1]
            batch = parts[-2]

    if testcode and testcode.isdigit():
        testcode = int(testcode)
    else:
        testcode = None  # Ensure testcode is None if not a valid integer

    return get_or_create(
        session,
        Sample,
        name=name,
        run_id=run_id,
        defaults={
            "is_control": is_control,
            "sex": sex,
            "batch": batch,
            "testcode": testcode,
        },
    )


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


def read_multiqc_data(project_id: str, file_id: str) -> dict:
    """
    Reads MultiQC data from a DNAnexus MultiQC JSON file.
    """
    with dxpy.open_dxfile(file_id, project_id) as dx_file:
        multiqc_data = json.load(dx_file)["report_saved_raw_data"]
        return multiqc_data


def parse_multiqc_section(section_data: dict) -> pd.DataFrame:
    """
    Parses a MultiQC section data dictionary into a DataFrame.
    """
    df = (
        pd.DataFrame.from_dict(section_data, orient="index")
        .reset_index()
        .rename(columns={"index": "sample"})
    )
    return df


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

        metadata = get_project_metadata(project_id, file_id)
        run_folder = metadata["run_folder"]

        multiqc_data = read_multiqc_data(project_id, file_id)

        with Session(engine) as session:
            # Get or Create Assay and Run Objects
            assay = get_or_create(
                session,
                Assay,
                name=metadata["assay"],
                ref_genome=metadata["ref_genome"],
            )

            run_defaults = {
                "run_folder": run_folder,
                "date": metadata["date"],
                "sequencer_id": metadata["sequencer_id"],
                "assay_id": assay.id,
            }
            run = get_or_create(session, Run, source=source, defaults=run_defaults)

            # Single check to see if the run has already been processed
            if run.processed_at:
                logging.info(f"Skipping {run.run_folder}, already processed.")
                return

            for section_name, section_data in multiqc_data.items():
                model = model_map.get(section_name)
                if not model:
                    if section_name not in IGNORE_SECTIONS:
                        logger.warning(f"No model for section: '{section_name}'")
                    continue

                df = parse_multiqc_section(section_data)
                if df.empty:
                    logger.warning(f"Empty df for {section_name}")
                    continue

                logger.info(f"creating records for {section_name}")

                recs = model.bulk_create_from_df(
                    session=session,
                    df=df,
                    run=run,
                    get_or_create_sample=get_or_create_sample,
                )
                logging.debug(f"Added {recs} records for {section_name}")

            run.processed_at = datetime.utcnow()
            session.commit()
            logging.info(
                f"Successfully processed and committed records in {run_folder}"
            )

    except Exception as e:
        logger.error(
            f"Failed to process {run_folder} -- {source}: {e}",
            exc_info=True,
        )


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

    live_reports = df[df["archival_state"] == "live"]
    if live_reports.empty:
        logger.warning("All found reports are archived. Exiting.")
        return

    logger.info(f"Starting ETL pipeline for {len(live_reports)} MultiQC reports...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(process_report, row.project_id, row.file_id, model_map)
            for row in live_reports.itertuples(index=False)
        ]
        for future in as_completed(futures):
            future.result()

    logger.info("Pipeline execution complete.")


if __name__ == "__main__":
    fire.Fire(main)
