import logging
import re
from collections import defaultdict

import fire
import pandas as pd
from sqlmodel import Session, create_engine, select

from data.config import DATABASE_PATH
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
from data.models.reports import Assay, Run, Sample
from data.models.sex_check import SexCheck

logger = logging.getLogger(__name__)

SPECIMEN_ID_PREFIX = re.compile(r"^SP-", re.IGNORECASE)
NGS_PROCEDURE_NAMES = ["CEN NGS", "WES NGS"]
ASSAY_NAMES = ["CEN38", "TWE38"]


def _strip_specimen_id(specimen_identifier: str) -> str:
    return SPECIMEN_ID_PREFIX.sub("", str(specimen_identifier).strip())


def _build_specimen_lookup(
    session: Session,
) -> dict[str, list[tuple[Sample, SexCheck | None]]]:
    """Maps the specimen id segment (index 1 of sample.name split on '-') to samples."""
    statement = (
        select(Sample, SexCheck, Assay.name)
        .join(SexCheck, SexCheck.sample_id == Sample.id, isouter=True)
        .join(Run, Run.id == Sample.run_id)
        .join(Assay, Assay.id == Run.assay_id)
        .where(Assay.name.in_(ASSAY_NAMES))
    )
    lookup: dict[str, list[tuple[Sample, SexCheck | None, str]]] = defaultdict(list)

    for sample, sex_check_row, assay_name in session.exec(statement).all():
        segments = sample.name.split("-")
        if len(segments) < 2:
            continue
        lookup[segments[1]].append((sample, sex_check_row, assay_name))

    return lookup


def _build_result_row(
    specimen_id: str,
    matches: list[tuple[Sample, SexCheck | None, str]] | None,
) -> dict:
    if not matches:
        return {
            "specimen_id": specimen_id,
            "sample_name": None,
            "run_folder": None,
            "assay_name": None,
            "matched": None,
            "reported_sex": None,
            "predicted_sex": None,
            "score": None,
            "mapped_chry": None,
            "mapped_chr1": None,
            "found_in_db": False,
        }

    if len(matches) > 1:
        logger.warning(
            "Specimen ID %s matched %d samples: %s. Using the first match.",
            specimen_id,
            len(matches),
            [sample.name for sample, _, _ in matches],
        )

    sample, sex_check_row, assay_name = matches[0]
    return {
        "specimen_id": specimen_id,
        "sample_name": sample.name,
        "run_folder": sample.run.run_folder,
        "assay_name": assay_name,
        "matched": sex_check_row.matched if sex_check_row else None,
        "reported_sex": (str(sex_check_row.reported_sex) if sex_check_row else None),
        "predicted_sex": (str(sex_check_row.predicted_sex) if sex_check_row else None),
        "score": (
            round(sex_check_row.score, 2) if sex_check_row is not None else None
        ),
        "mapped_chry": sex_check_row.mapped_chry if sex_check_row else None,
        "mapped_chr1": sex_check_row.mapped_chr1 if sex_check_row else None,
        "found_in_db": True,
    }


def build_sex_check_report(session: Session, specimen_ids: list[str]) -> pd.DataFrame:
    lookup = _build_specimen_lookup(session)
    rows = [
        _build_result_row(specimen_id, lookup.get(specimen_id))
        for specimen_id in specimen_ids
    ]
    return pd.DataFrame(rows)


def main(
    input_path: str = "data/samples.txt",
    output_path: str = "data/sex_check_resultv2.xlsx",
) -> None:
    input_df = pd.read_csv(input_path, sep="\t")
    specimen_ids = input_df["samples"].map(_strip_specimen_id).tolist()
    
    print(f"[INFO] Found {len(specimen_ids)} specimen IDs in {input_path}.")

    engine = create_engine(f"sqlite:///{DATABASE_PATH}")
    with Session(engine) as session:
        result_df = build_sex_check_report(session, specimen_ids)

    result_df.to_excel(output_path, index=False)
    print(f"[SUCCESS] Wrote {len(result_df)} row(s) to {output_path}.")


if __name__ == "__main__":
    fire.Fire(main)
