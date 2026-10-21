import re
from typing import TYPE_CHECKING, Any

import pandas as pd
from sqlmodel import Session, select

if TYPE_CHECKING:
    from data.models.reports import Sample

from data.utils.multiqc import parse_multiqc_section
from data.utils.utils import get_sample_metadata, standardise_column_names


def clean_sample_name(name: str) -> str:
    """
    Cleans a sample name by stripping Illumina run-specific suffixes (_S1_L001...)
    and trailing file extensions (.bam, .alignment, .cram, .hsmetrics, .star).
    """
    if not isinstance(name, str):
        return ""

    cleaned = re.sub(r"_S\d+.*$", "", name)
    cleaned = re.sub(
        r"\.(?:bam|alignment|cram|hsmetrics|star)$", "", cleaned, flags=re.IGNORECASE
    )
    return cleaned.strip()


def extract_sample_number(name: str) -> str | None:
    """
    Extracts the Illumina sample number (e.g., 'S7', 'S1') from a sample name.
    The sample number is prefixed with 'S' followed by digits and bounded by
    underscores or the end of the string.
    Example: '125377319-23262S0013-23TSOD54-8471_S7_L001_R1' -> 'S7'
    """
    if not isinstance(name, str):
        return None

    match = re.search(r"_(S\d+)(?:_|$)", name)
    return match.group(1) if match else None


def _format_well_coord(val: Any) -> str | None:
    """
    Formats a well row or column coordinate into a string category value,
    or None if empty or NaN.
    """
    if val is None or pd.isna(val):
        return None

    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "<na>", "null"):
        return None

    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except ValueError:
        pass

    return s


def extract_run_samples_metadata(multiqc_data: dict) -> dict[str, dict[str, Any]]:
    """
    Extracts run samples and their metadata (sample_number, well_col, well_row)
    from multiqc_data.

    All runs are expected to contain 'multiqc_fastqc' data. Raises ValueError
    if missing or empty.
    """
    if not (fastqc_data := multiqc_data.get("multiqc_fastqc")):
        raise ValueError("Missing required 'multiqc_fastqc' section in MultiQC data")

    df_fastqc = parse_multiqc_section(fastqc_data)
    if df_fastqc.empty or "sample" not in df_fastqc.columns:
        raise ValueError("'multiqc_fastqc' section contains no sample records")

    samples: dict[str, dict[str, Any]] = {}

    for raw_name in df_fastqc["sample"].dropna():
        clean_name = clean_sample_name(raw_name)
        if not clean_name or clean_name.lower().startswith("undetermined"):
            continue

        sample_num = extract_sample_number(raw_name)
        if clean_name not in samples:
            samples[clean_name] = {
                "sample_number": sample_num,
                "well_col": None,
                "well_row": None,
            }
        elif sample_num and not samples[clean_name]["sample_number"]:
            samples[clean_name]["sample_number"] = sample_num

    # Extract well coordinates and sample_number from general stats if present
    if gen_data := multiqc_data.get("multiqc_general_stats"):
        df_gen = parse_multiqc_section(gen_data)
        if not df_gen.empty and "sample" in df_gen.columns:
            df_std = standardise_column_names(df_gen.copy())
            col_col = next(
                (
                    c
                    for c in (
                        "custom_content_samplesheet_wells_well_column",
                        "well_column",
                        "well_col",
                    )
                    if c in df_std.columns
                ),
                None,
            )
            row_col = next(
                (
                    c
                    for c in (
                        "custom_content_samplesheet_wells_well_row",
                        "well_row",
                    )
                    if c in df_std.columns
                ),
                None,
            )

            for _, row in df_std.iterrows():
                clean_name = clean_sample_name(row["sample"])
                if clean_name in samples:
                    if col_col and (val := _format_well_coord(row.get(col_col))):
                        samples[clean_name]["well_col"] = val
                    if row_col and (val := _format_well_coord(row.get(row_col))):
                        samples[clean_name]["well_row"] = val
                    if not samples[clean_name]["sample_number"] and (
                        s_num := extract_sample_number(str(row["sample"]))
                    ):
                        samples[clean_name]["sample_number"] = s_num

    return samples


def get_or_create_run_samples(
    session: Session, multiqc_data: dict, run_id: int
) -> dict[str, Any]:
    """
    Extracts run samples from multiqc_data and gets or creates them in the database
    for the given run_id.

    Returns a dictionary mapping clean sample names to Sample instances.
    """
    from data.models.reports import Sample # noqa: F401 - imported on first use

    sample_metadata_map = extract_run_samples_metadata(multiqc_data)

    stmt = select(Sample).where(Sample.run_id == run_id)
    existing_samples = session.exec(stmt).all()
    sample_map: dict[str, Sample] = {s.name: s for s in existing_samples}

    new_or_updated = False
    for clean_name, info in sample_metadata_map.items():
        base_meta = get_sample_metadata(clean_name)

        if sample := sample_map.get(clean_name):
            for field in ("sample_number", "well_col", "well_row"):
                if getattr(sample, field) is None and info.get(field):
                    setattr(sample, field, info[field])
                    new_or_updated = True
            session.add(sample)
        else:
            sample = Sample(
                name=clean_name,
                run_id=run_id,
                sample_number=info.get("sample_number"),
                well_col=info.get("well_col"),
                well_row=info.get("well_row"),
                is_control=base_meta["is_control"],
                sex=base_meta["sex"],
                batch=base_meta["batch"],
                testcode=base_meta["testcode"],
            )
            session.add(sample)
            sample_map[clean_name] = sample
            new_or_updated = True

    if new_or_updated:
        session.flush()
        for s in sample_map.values():
            session.refresh(s)

    return sample_map
