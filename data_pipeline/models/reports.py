import re
from datetime import datetime
from pydantic import StringConstraints, ConfigDict, BeforeValidator
from sqlalchemy import func
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint, Session, select
import pandas as pd 
from typing import ClassVar, Type, Annotated, get_args

import logging


from .choices import SexKaryotype, QCStatus


class Assay(SQLModel, table=True):
    """Model for a bioinformatics assay/test type."""

    __tablename__ = "assay"
    # The combination of assay name and reference genome must be unique.
    __table_args__ = (
        UniqueConstraint("name", "ref_genome", name="unique_assay_genome"),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Name of the assay (e.g., CEN, TWE)")
    test_code: int | None = Field(
        default=None, description="Internal lab code for the analysis"
    )
    ref_genome: str | None = Field(
        default=None, description="Reference genome build (e.g., B37, B38)"
    )

    runs: list["Run"] = Relationship(back_populates="assay")


class Run(SQLModel, table=True):
    """Model for a sequencing/analysis run, usually corresponds to a DNAnexus project."""

    __tablename__ = "run"
    id: int | None = Field(default=None, primary_key=True)
    run_folder: str = Field(index=True, description="Name of the sequencing run")
    date: datetime = Field(description="Date of the sequencing run")
    sequencer_id: str = Field(description="ID of the sequencing instrument")
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
    picard_alignment_summary_metrics: list[
        "PicardAlignmentSummaryMetrics"
    ] = Relationship(back_populates="sample")
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
    sentieon_alignment_summary_metrics: list[
        "SentieonAlignmentSummaryMetrics"
    ] = Relationship(back_populates="sample")
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


###############################################################################


class BaseMetrics(SQLModel):
    """
    An abstract base model for all metric tables.

    It includes class-level configurations that should be overridden by subclasses
    and class methods to handle data processing and database interaction.
    """

    model_config = ConfigDict(populate_by_name=True)

    multiqc_section_names: ClassVar[list[str]] = []
    index_col: ClassVar[str] = "sample"

    id: int | None = Field(
        default=None, primary_key=True, description="Primary key for the metric record"
    )
    sample_id: int = Field(
        foreign_key="sample.id", description="Foreign key linking to the sample"
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
    def coerce_numeric_columns(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Coerces numeric fields in the DataFrame based on model field annotations.
        Turns conversion errors into NaN values.
        """
        for field_name, model_field in cls.model_fields.items():
            if field_name in df.columns:
                # Handle simple types (e.g. float) and Union types (e.g. float | None)
                field_types = get_args(model_field.annotation) or (
                    model_field.annotation,
                )
                if any(t in (int, float) for t in field_types):
                    df[field_name] = pd.to_numeric(df[field_name], errors="coerce")
        return df

    @classmethod
    def has_existing_records(cls, session: Session, run: "Run") -> bool:
        """Checks if any metric records of this type already exist for a given run."""
        existing_count = session.exec(
            select(func.count())
            .select_from(cls)
            .join(Sample, cls.sample_id == Sample.id)
            .where(Sample.run_id == run.id)
        ).one()
        return existing_count > 0

    @classmethod
    def bulk_create_from_df(
        cls,
        session: Session,
        df: pd.DataFrame,
        run: Run,
        get_or_create_sample: callable,
    ) -> int:
        """Processes a DataFrame and bulk-creates metric instances in the database."""
        
        if cls.has_existing_records(session, run):
            logging.warning(
                f"Skipping {cls.__name__} - already processed for {run.run_folder}"
            )
            return 0
        
        df = cls.custom_transform(df)
        
        # This prevents pydantic validation errors for 'nan' values.
        df = df.where(pd.notna(df), None)

        index_col = cls.index_col

        df = df.dropna(subset=[index_col])
        df = df[~df[index_col].astype(str).str.lower().str.startswith("undetermined")]

        records_to_create = []
        for record in df.to_dict(orient="records"):
            sample_name = record.get(index_col)

            sample = get_or_create_sample(
                session=session, name=sample_name, run_id=run.id
            )
            metric_data = record.copy()
            metric_data["sample_id"] = sample.id

            records_to_create.append(cls.model_validate(metric_data))

        if records_to_create:
            session.add_all(records_to_create)

        return len(records_to_create)
