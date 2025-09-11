import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Type, get_args

import dxpy
import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from data_pipeline.models.choices import SexKaryotype
from data_pipeline.models.reports import Assay, Run, Sample, BaseMetrics
from data_pipeline.models import (
    bcl2fastq,
    fastqc,
    happy,
    picard,
    samtools,
    sentieon,
    sex_check,
    somalier,
    sompy,
    tso500,
    vcfqc,
    verifybamid,
)

from .utils import clean_df, get_project_metadata

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "data_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DATABASE_FILE = "verity_db.sqlite3"
DATABASE_PATH = PROJECT_ROOT / "data" / DATABASE_FILE
MQC_DATA_SOURCE = PROJECT_ROOT / "data" / "VERITY_DATASET" / "source" / "mqc_data.tsv"
MAX_WORKERS = 16

engine = create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"timeout": 60})


def create_db_and_tables() -> None:
    """Creates the database and all tables based on the SQLModel metadata."""
    logging.info("Initialising database and creating tables if they don't exist...")

    DATABASE_PATH.parent.mkdir(exist_ok=True, parents=True)
    SQLModel.metadata.create_all(engine)

    logging.info("Database and tables initialised.")


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

    control_pattern = r"-[0-9]+Q[0-9]+-|NA12878.*"
    is_control = bool(re.search(control_pattern, name))

    # TODO: refactor to accomodate HRD runs
    sex = SexKaryotype.UNKNOWN
    parts = name.split("-")
    if len(parts) > 2:
        sex = SexKaryotype(parts[-2])

    return get_or_create(
        session,
        Sample,
        name=name,
        run_id=run_id,
        defaults={"is_control": is_control, "sex": sex},
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

            for section_name, section_data in multiqc_data.items():
                model = model_map.get(section_name)
                if not model:
                    continue

                df = parse_multiqc_section(section_data)
                if df.empty:
                    continue

                df = clean_df(df)
                df = model.coerce_numeric_columns(df)

                model.bulk_create_from_df(
                    session=session,
                    df=df,
                    run=run,
                    get_or_create_sample=get_or_create_sample,
                )
            session.commit()
            logging.info(
                f"Successfully processed and committed records in {run_folder}"
            )

    except Exception as e:
        logging.error(
            f"Failed to process {run_folder} -- {source}: {e}",
            exc_info=True,
        )


def main() -> None:
    """
    Entry point to run the entire ETL pipeline.

    `find_mqc_data.py` wrote the MQC_DATA_SOURCE; It contains IDs of multiqc_data.json files
    Subset df (as you like) to add only desired projects/files.

    A gentle reminder to ensure files are live before running this pipeline!
    """

    create_db_and_tables()
    model_map = get_mqc_to_models()

    try:
        df = pd.read_csv(MQC_DATA_SOURCE, sep="\t")
        df = df[df["archival_state"] == "live"]
    except FileNotFoundError:
        logging.error(f"Source data file not found: {MQC_DATA_SOURCE}. Aborting.")
        return

    logging.info(f"Starting ETL pipeline for {len(df)} MultiQC reports...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(process_report, row.project_id, row.file_id, model_map)
            for row in df.itertuples(index=False)
        ]
        for future in as_completed(futures):
            future.result()  # Exceptions are handled in threads gracefully

    logging.info("Pipeline execution complete.")


if __name__ == "__main__":
    main()
