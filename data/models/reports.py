import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Callable, ClassVar, Type, get_args

import pandas as pd
from pydantic import BeforeValidator, ConfigDict, StringConstraints
from sqlalchemy import func
from sqlmodel import Field, Relationship, Session, SQLModel, UniqueConstraint, select

from ..utils import standardise_column_names
from .choices import QCStatus, SexKaryotype

if TYPE_CHECKING:
    from .bcl2fastq import Bcl2fastqByLane, Bcl2fastqBySample
    from .bclconvert import BclconvertByLane, BclconvertBySample
    from .fastqc import Fastqc
    from .happy import HappyIndel, HappySnp
    from .interop import IndexSummary, RunSummary
    from .picard import (
        PicardAlignmentSummaryMetrics,
        PicardBaseContent,
        PicardDups,
        PicardGcBias,
        PicardHsMetrics,
        PicardInsertSize,
        PicardPcrMetrics,
        PicardQualityYieldMetrics,
        PicardRnaSeqMetrics,
        PicardVariantCalling,
    )
    from .rna_seqc import RnaSeqc
    from .samtools import SamtoolsFlagstat
    from .sentieon import SentieonAlignmentSummaryMetrics, SentieonInsertSize
    from .sex_check import SexCheck
    from .somalier import SomalierSexCheck
    from .sompy import Sompy
    from .tso500 import Tso500MetricsOutputDna
    from .vcfqc import VcfQcHetHom
    from .verifybamid import VerifyBamId


class classproperty(property):
    """
    A decorator that combines @classmethod and @property.

    Allows a method to be accessed as a property of the class.
    """

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


def _get_categorical_fields(cls) -> list[str]:
    """
    Inspects a SQLModel and returns a sorted list of its categorical field names.
    """
    categorical_fields = []
    exclude_fields = {
        "id",
        "sample_id",
        "run_id",
        "assay_id",
        "source",
        "filename",
        "sample",
        "name",
        "library",
        "rg",
        "run_folder",
        "date",
        "sequencer_id",
        "processed_at",
    }

    for field_name, model_field in cls.model_fields.items():
        if field_name in exclude_fields:
            continue

        field_types = get_args(model_field.annotation) or (model_field.annotation,)

        if any(t in (str, bool) for t in field_types) or any(
            isinstance(t, type) and issubclass(t, (QCStatus, SexKaryotype))
            for t in field_types
        ):
            categorical_fields.append(field_name)

    return sorted(categorical_fields)


class Assay(SQLModel, table=True):
    """Model for a bioinformatics assay/test type."""

    __tablename__ = "assay"
    __table_args__ = (
        UniqueConstraint("name", "ref_genome", name="unique_assay_genome"),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Name of the assay (e.g., CEN, TWE)")
    ref_genome: str | None = Field(
        default=None, description="Reference genome build (e.g., B37, B38)"
    )

    runs: list["Run"] = Relationship(back_populates="assay")

    @classmethod
    @classproperty
    def categorical_fields(cls) -> list[str]:
        return _get_categorical_fields(cls)


class Run(SQLModel, table=True):
    """Model for a sequencing run, usually corresponds to a DNAnexus project."""

    __tablename__ = "run"
    id: int | None = Field(default=None, primary_key=True)
    run_folder: str = Field(index=True, description="Name of the sequencing run")
    date: datetime = Field(description="Date of the sequencing run")
    sequencer_id: str = Field(description="ID of the sequencing instrument")
    processed_at: datetime | None = Field(
        default=None, description="Timestamp of when the report was added to DB"
    )
    qc_status: QCStatus = Field(
        default=QCStatus.NOTREPORTED, description="The QC status of this run"
    )
    source: Annotated[
        str,
        StringConstraints(pattern=r"^project-[a-zA-Z0-9]{24}:file-[a-zA-Z0-9]{24}$"),
    ] = Field(
        unique=True,
        index=True,
        description="DNAnexus file ID of the source multiqc json file",
    )

    assay_id: int = Field(
        foreign_key="assay.id", description="Foreign key to the assay"
    )
    assay: "Assay" = Relationship(back_populates="runs")
    samples: list["Sample"] = Relationship(back_populates="run")

    # Relationships to all associated run-level metrics for this run
    bcl2fastq_bylane_metrics: list["Bcl2fastqByLane"] = Relationship(
        back_populates="run"
    )
    bclconvert_bylane_metrics: list["BclconvertByLane"] = Relationship(
        back_populates="run"
    )
    interop_runsummary_metrics: list["RunSummary"] = Relationship(back_populates="run")
    interop_indexsummary_metrics: list["IndexSummary"] = Relationship(
        back_populates="run"
    )

    @classmethod
    @classproperty
    def categorical_fields(cls) -> list[str]:
        return _get_categorical_fields(cls)


class Sample(SQLModel, table=True):
    """Model for a sample."""

    __tablename__ = "sample"
    # A sample name should be unique within the context of a single run.
    __table_args__ = (UniqueConstraint("name", "run_id", name="unique_sample_in_run"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="The name of the sample")
    sex: SexKaryotype = Field(
        default=SexKaryotype.UNKNOWN, description="Reported sex of the sample"
    )
    is_control: bool = Field(
        default=False, description="Flag indicating if the sample is a control"
    )
    qc_status: QCStatus = Field(
        default=QCStatus.NOTREPORTED, description="The final QC verdict of the sample"
    )
    batch: str = Field(default="", description="The Epic batch the sample belongs to")
    testcode: int | None = Field(
        default=None, description="The Epic test the sample was booked for"
    )

    run_id: int = Field(
        foreign_key="run.id", description="Foreign key linking to the run"
    )
    run: "Run" = Relationship(back_populates="samples")

    # Relationships to all associated metrics for this sample
    samtools_flagstat_metrics: list["SamtoolsFlagstat"] = Relationship(
        back_populates="sample"
    )
    happy_indel_metrics: list["HappyIndel"] = Relationship(back_populates="sample")
    happy_snp_metrics: list["HappySnp"] = Relationship(back_populates="sample")
    vcfqc_hethom_metrics: list["VcfQcHetHom"] = Relationship(back_populates="sample")
    fastqc_metrics: list["Fastqc"] = Relationship(back_populates="sample")
    bcl2fastq_bysample_metrics: list["Bcl2fastqBySample"] = Relationship(
        back_populates="sample"
    )
    bclconvert_bysample_metrics: list["BclconvertBySample"] = Relationship(
        back_populates="sample"
    )
    picard_alignment_summary_metrics: list["PicardAlignmentSummaryMetrics"] = (
        Relationship(back_populates="sample")
    )
    picard_base_content_metrics: list["PicardBaseContent"] = Relationship(
        back_populates="sample"
    )
    picard_dups_metrics: list["PicardDups"] = Relationship(back_populates="sample")
    picard_gcbias_metrics: list["PicardGcBias"] = Relationship(back_populates="sample")
    picard_hs_metrics: list["PicardHsMetrics"] = Relationship(back_populates="sample")
    picard_insert_size_metrics: list["PicardInsertSize"] = Relationship(
        back_populates="sample"
    )
    picard_pcr_metrics: list["PicardPcrMetrics"] = Relationship(back_populates="sample")
    picard_quality_yield_metrics: list["PicardQualityYieldMetrics"] = Relationship(
        back_populates="sample"
    )
    picard_variant_calling_metrics: list["PicardVariantCalling"] = Relationship(
        back_populates="sample"
    )
    rna_seqc_metrics: list["RnaSeqc"] = Relationship(back_populates="sample")
    picard_rnaseq_metrics: list["PicardRnaSeqMetrics"] = Relationship(
        back_populates="sample"
    )
    sentieon_alignment_summary_metrics: list["SentieonAlignmentSummaryMetrics"] = (
        Relationship(back_populates="sample")
    )
    sentieon_insert_size_metrics: list["SentieonInsertSize"] = Relationship(
        back_populates="sample"
    )
    sex_check_metrics: list["SexCheck"] = Relationship(back_populates="sample")
    somalier_sex_check_metrics: list["SomalierSexCheck"] = Relationship(
        back_populates="sample"
    )
    sompy_metrics: list["Sompy"] = Relationship(back_populates="sample")
    tso500_metrics_output_dna: list["Tso500MetricsOutputDna"] = Relationship(
        back_populates="sample"
    )
    verifybamid_metrics: list["VerifyBamId"] = Relationship(back_populates="sample")

    @classmethod
    @classproperty
    def categorical_fields(cls) -> list[str]:
        return _get_categorical_fields(cls)


###################################################################################################


class BaseMetrics(SQLModel):
    """
    An abstract base model for all metric tables.

    It includes class-level configurations that should be overridden by subclasses
    and class methods to handle data processing and database interaction.
    """

    model_config = ConfigDict(populate_by_name=True)
    _numeric_fields_cache: ClassVar[list[str] | None] = None

    multiqc_section_names: ClassVar[list[str]] = []
    index_col: ClassVar[str] = "sample"
    metric_level: ClassVar[str] = "sample"  # 'sample' or 'run'

    id: int | None = Field(
        default=None, primary_key=True, description="Primary key for the metric record"
    )
    # Should set sample to None for run-level metrics and define run_id instead
    sample_id: int = Field(
        foreign_key="sample.id",
        description="Foreign key linking to the sample",
    )

    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        A hook for custom data transformations.

        Subclasses can override this to perform tool-specific data manipulations.
        Most reasonable default is return as-is.
        """
        return df

    @classmethod
    def _clean_sample_names(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans sample names by stripping run-specific suffixes and extracts
        metadata (flow cell, lane, read pair) into separate columns if they exist.
        """
        sample_col = cls.index_col
        if sample_col not in df.columns:
            return df

        # Regex to find suffixes like _S1_L001_R1_001 or _S22_L001_sorted
        suffix = r"_S\d+.*$"

        flowcell = r"(S\d+)"
        lane = r"(L\d+)"
        readpair = r"(R[12])"

        df["flow_cell"] = df[sample_col].str.extract(flowcell, expand=False)
        df["lane"] = df[sample_col].str.extract(lane, expand=False)
        df["read_pair"] = df[sample_col].str.extract(readpair, expand=False)

        # Clean the original sample name by removing the entire suffix
        df[sample_col] = df[sample_col].str.replace(suffix, "", regex=True)

        # Drop rows where the sample name is 'undetermined'
        df = df.dropna(subset=[sample_col])
        df = df[~df[sample_col].astype(str).str.lower().str.startswith("undetermined")]

        return df

    @classmethod
    @classproperty
    def numeric_fields(cls) -> list[str]:
        """
        Returns a cached list of numeric field names for the model, excluding IDs.

        This is a class property that inspects the model's fields, identifies those
        with numeric types (int, float), and caches the result for reuse.
        """
        if cls._numeric_fields_cache is not None:
            return cls._numeric_fields_cache

        numeric_fields = []
        # Exclude DB IDs as they are not metrics for plotting
        excluded_fields = {"id", "sample_id", "run_id"}

        for field_name, model_field in cls.model_fields.items():
            if field_name in excluded_fields:
                continue

            # Handle simple types (e.g. float) and Union types (e.g. float | None)
            field_types = get_args(model_field.annotation) or (model_field.annotation,)
            if any(t in (int, float) for t in field_types):
                numeric_fields.append(field_name)

        cls._numeric_fields_cache = numeric_fields
        return numeric_fields

    @classmethod
    @classproperty
    def display_name(cls) -> str:
        """
        Returns a user-friendly name for the tool.
        e.g. "SamtoolsFlagstat" -> "Samtools Flagstat"
        """
        return re.sub(r"(?<!^)(?=[A-Z])", " ", cls.__name__)

    @classmethod
    @classproperty
    def plotting_fields(cls) -> list[str]:
        """Returns fields valid for Y-axis plotting. Defaults to numeric_fields."""
        return cls.numeric_fields

    @classmethod
    @classproperty
    def categorical_fields(cls) -> list[str]:
        """Returns fields valid for grouping/coloring."""
        return _get_categorical_fields(cls)

    @classmethod
    def coerce_numeric_columns(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Coerces numeric fields in the DataFrame based on model field annotations.
        Turns conversion errors into NaN values.
        """
        for col in cls.numeric_fields:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    @classmethod
    def clean_df(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardises, cleans, and coerces dtypes for a given DataFrame.
        """
        df = standardise_column_names(df)
        if cls.metric_level == "sample":
            df = cls._clean_sample_names(df)
        df = df.convert_dtypes()
        df = cls.coerce_numeric_columns(df)
        df = df.where(pd.notna(df), None)
        return df

    @classmethod
    def bulk_create_from_df(
        cls,
        session: Session,
        df: pd.DataFrame,
        run: Run,
        get_or_create_sample: Callable[[Session, str, int], "Sample"],
    ) -> int:
        """Processes a DataFrame and bulk-creates metric instances in the database."""

        df = cls.clean_df(df)
        df = cls.custom_transform(df)
        df = df.where(pd.notna(df), None)

        records_to_create = []
        for record in df.to_dict(orient="records"):
            metric_data = record.copy()

            if cls.metric_level == "sample":
                sample_name = record.get(cls.index_col)
                sample = get_or_create_sample(
                    session=session, name=sample_name, run_id=run.id
                )
                metric_data["sample_id"] = sample.id
            elif cls.metric_level == "run":
                metric_data["run_id"] = run.id

            records_to_create.append(cls.model_validate(metric_data))

        if records_to_create:
            session.add_all(records_to_create)

        return len(records_to_create)
