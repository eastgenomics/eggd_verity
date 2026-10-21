"""Tests for sample extraction, cleaning, and run sample discovery utilities."""

from datetime import datetime
import pandas as pd
import pytest
from sqlmodel import Session, select

from data.models.choices import SexKaryotype
from data.models.gen_stats import GenStats
from data.models.reports import Assay, Run, Sample
from data.utils.sample import (
    clean_sample_name,
    extract_run_samples_metadata,
    extract_sample_number,
    get_or_create_run_samples,
)


def test_clean_sample_name():
    # Illumina run suffixes
    assert (
        clean_sample_name("125377319-23262S0013-23TSOD54-8471_S7_L001_R1")
        == "125377319-23262S0013-23TSOD54-8471"
    )
    assert (
        clean_sample_name("125377319-23262S0013-23TSOD54-8471_S7_L002_R2")
        == "125377319-23262S0013-23TSOD54-8471"
    )
    assert clean_sample_name("Sample1_S1_L001_R1_001") == "Sample1"
    assert clean_sample_name("Sample2_S22_L001_sorted") == "Sample2"

    # File extensions
    assert clean_sample_name("SampleA.bam") == "SampleA"
    assert clean_sample_name("SampleB.alignment") == "SampleB"
    assert clean_sample_name("SampleC.cram") == "SampleC"
    assert clean_sample_name("SampleD.hsmetrics") == "SampleD"
    assert clean_sample_name("SampleE.star") == "SampleE"
    assert clean_sample_name("SampleF.BAM") == "SampleF"

    # Preserve internal 'S' in batch/sample name
    assert (
        clean_sample_name("125377319-23262S0013-23TSOD54-8471")
        == "125377319-23262S0013-23TSOD54-8471"
    )

    # Edge cases
    assert clean_sample_name("") == ""
    assert clean_sample_name(None) == ""


def test_extract_sample_number():
    assert (
        extract_sample_number("125377319-23262S0013-23TSOD54-8471_S7_L001_R1")
        == "S7"
    )
    assert (
        extract_sample_number("125377319-23262S0013-23TSOD54-8471_S7_L002_R2")
        == "S7"
    )
    assert extract_sample_number("sample_S1_L001_R1") == "S1"
    assert extract_sample_number("sample_S10") == "S10"

    # Internal 'S' in batch name (e.g., 23262S0013, 23TSOD54) must not be matched
    assert (
        extract_sample_number("125377319-23262S0013-23TSOD54-8471")
        is None
    )
    assert extract_sample_number("sample-without-suffix") is None
    assert extract_sample_number(None) is None


def test_extract_run_samples_metadata_from_fastqc():
    multiqc_data = {
        "multiqc_fastqc": {
            "125377319-23262S0013-23TSOD54-8471_S7_L001_R1": {"total_sequences": 1000},
            "125377319-23262S0013-23TSOD54-8471_S7_L001_R2": {"total_sequences": 1000},
            "125377319-23262S0013-23TSOD54-8471_S7_L002_R1": {"total_sequences": 1000},
            "125377319-23262S0013-23TSOD54-8471_S7_L002_R2": {"total_sequences": 1000},
            "Sample2_S8_L001_R1": {"total_sequences": 2000},
            "Undetermined_S0_L001_R1": {"total_sequences": 500},
        }
    }

    metadata = extract_run_samples_metadata(multiqc_data)

    assert len(metadata) == 2
    assert "125377319-23262S0013-23TSOD54-8471" in metadata
    assert metadata["125377319-23262S0013-23TSOD54-8471"]["sample_number"] == "S7"
    assert metadata["125377319-23262S0013-23TSOD54-8471"]["well_col"] is None
    assert metadata["125377319-23262S0013-23TSOD54-8471"]["well_row"] is None

    assert "Sample2" in metadata
    assert metadata["Sample2"]["sample_number"] == "S8"
    assert "Undetermined" not in metadata


def test_extract_run_samples_metadata_with_general_stats_wells():
    multiqc_data = {
        "multiqc_fastqc": {
            "Sample1_S7_L001_R1": {"total_sequences": 1000},
            "Sample2_S8_L001_R1": {"total_sequences": 2000},
        },
        "multiqc_general_stats": {
            "Sample1": {
                "custom_content_samplesheet_wells_well_column": 1,
                "custom_content_samplesheet_wells_well_row": "A",
            },
            "Sample2": {
                "custom_content_samplesheet_wells_well_column": 12.0,
                "custom_content_samplesheet_wells_well_row": "H",
            },
        },
    }

    metadata = extract_run_samples_metadata(multiqc_data)

    assert metadata["Sample1"]["sample_number"] == "S7"
    assert metadata["Sample1"]["well_col"] == "1"
    assert metadata["Sample1"]["well_row"] == "A"

    assert metadata["Sample2"]["sample_number"] == "S8"
    assert metadata["Sample2"]["well_col"] == "12"
    assert metadata["Sample2"]["well_row"] == "H"


def test_extract_run_samples_metadata_missing_fastqc_raises():
    with pytest.raises(ValueError, match="Missing required 'multiqc_fastqc' section"):
        extract_run_samples_metadata({})

    with pytest.raises(ValueError, match="Missing required 'multiqc_fastqc' section"):
        extract_run_samples_metadata({"multiqc_fastqc": {}})


def test_extract_run_samples_metadata_multiplex_filtering():
    """
    In a multiplex run, general stats has rows for samples from both assays,
    but FastQC only contains samples belonging to the current run.
    """
    multiqc_data = {
        "multiqc_fastqc": {
            "RunA_Sample1_S1_L001_R1": {"total_sequences": 1000000},
            "RunA_Sample2_S2_L001_R1": {"total_sequences": 2000000},
        },
        "multiqc_general_stats": {
            "RunA_Sample1_S1": {
                "custom_content_samplesheet_wells_well_column": 3,
                "custom_content_samplesheet_wells_well_row": "C",
            },
            "RunA_Sample2_S2": {
                "custom_content_samplesheet_wells_well_column": 4,
                "custom_content_samplesheet_wells_well_row": "D",
            },
            # Foreign samples from another multiplexed assay:
            "RunB_Foreign1_S3": {
                "custom_content_samplesheet_wells_well_column": 5,
                "custom_content_samplesheet_wells_well_row": "E",
            },
            "RunB_Foreign2_S4": {
                "custom_content_samplesheet_wells_well_column": 6,
                "custom_content_samplesheet_wells_well_row": "F",
            },
        },
    }

    metadata = extract_run_samples_metadata(multiqc_data)

    assert "RunA_Sample1" in metadata
    assert "RunA_Sample2" in metadata
    assert "RunB_Foreign1" not in metadata
    assert "RunB_Foreign2" not in metadata

    assert metadata["RunA_Sample1"]["sample_number"] == "S1"
    assert metadata["RunA_Sample1"]["well_col"] == "3"
    assert metadata["RunA_Sample1"]["well_row"] == "C"


def test_get_or_create_run_samples(session: Session):
    assay = Assay(name="TSOD", ref_genome="GRCh38")
    session.add(assay)
    session.commit()

    run = Run(
        run_folder="RUN_TSOD_001",
        date=datetime(2026, 1, 1),
        sequencer_id="A01303",
        source="project-111111111111111111111111:file-111111111111111111111111",
        assay_id=assay.id,
    )
    session.add(run)
    session.commit()

    multiqc_data = {
        "multiqc_fastqc": {
            "125377319-23262S0013-23TSOD54-8471_S7_L001_R1": {"total_sequences": 1000},
            "125377319-23262S0013-23TSOD54-8471_S7_L001_R2": {"total_sequences": 1000},
        },
        "multiqc_general_stats": {
            "125377319-23262S0013-23TSOD54-8471": {
                "custom_content_samplesheet_wells_well_column": 2,
                "custom_content_samplesheet_wells_well_row": "B",
            }
        },
    }

    sample_map = get_or_create_run_samples(session, multiqc_data, run.id)

    assert "125377319-23262S0013-23TSOD54-8471" in sample_map
    sample = sample_map["125377319-23262S0013-23TSOD54-8471"]
    assert sample.id is not None
    assert sample.sample_number == "S7"
    assert sample.well_col == "2"
    assert sample.well_row == "B"
    assert sample.run_id == run.id

    # Re-running does not duplicate, but returns existing
    sample_map_2 = get_or_create_run_samples(session, multiqc_data, run.id)
    assert len(sample_map_2) == 1
    assert sample_map_2["125377319-23262S0013-23TSOD54-8471"].id == sample.id

    # Verify directly in DB
    all_db_samples = session.exec(select(Sample).where(Sample.run_id == run.id)).all()
    assert len(all_db_samples) == 1


def test_bulk_create_from_df_filters_multiplex_samples(session: Session):
    assay = Assay(name="TSOD", ref_genome="GRCh38")
    session.add(assay)
    session.commit()

    run = Run(
        run_folder="RUN_TSOD_002",
        date=datetime(2026, 1, 1),
        sequencer_id="A01303",
        source="project-333333333333333333333333:file-333333333333333333333333",
        assay_id=assay.id,
    )
    session.add(run)
    session.commit()

    sample_a = Sample(name="SampleA", run_id=run.id, sample_number="S1")
    session.add(sample_a)
    session.commit()

    sample_map = {"SampleA": sample_a}

    # Dataframe contains SampleA (part of run) and ForeignSample (from other assay)
    df = pd.DataFrame(
        [
            {
                "sample": "SampleA",
                "custom_content_custom_coverage_250x": 98.5,
            },
            {
                "sample": "ForeignSample",
                "custom_content_custom_coverage_250x": 95.0,
            },
        ]
    )

    created_count = GenStats.bulk_create_from_df(
        session=session,
        df=df,
        run=run,
        sample_map=sample_map,
    )

    assert created_count == 1
    records = session.exec(select(GenStats)).all()
    assert len(records) == 1
    assert records[0].sample_id == sample_a.id
    assert records[0].custom_coverage_250x == 98.5


def test_sample_categorical_fields():
    cat_fields = Sample.categorical_fields
    assert "sample_number" in cat_fields
    assert "well_col" in cat_fields
    assert "well_row" in cat_fields
