import re
from typing import TYPE_CHECKING, ClassVar

import pandas as pd
from sqlmodel import Field, Relationship

from .choices import QCStatus
from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Sample


class Fastqc(BaseMetrics, table=True):
    """Metrics from the FastQC tool."""

    __tablename__ = "fastqc"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_fastqc"]

    sample: "Sample" = Relationship(back_populates="fastqc_metrics")

    flow_cell: str | None = Field(default=None, description="Flow cell (eg S5)")
    lane: str | None = Field(default=None, description="Sequencing lane (eg L001)")
    read_pair: str | None = Field(default=None, description="Read pair (eg R1, R2)")

    # computed fields
    total_unique_reads: int | None = Field(
        default=None,
        description="Sum of unique reads for the sample across all lanes/pairs",
    )
    total_duplicate_reads: int | None = Field(
        default=None,
        description="Sum of duplicate reads for the sample across all lanes/pairs",
    )

    filename: str
    file_type: str
    encoding: str

    total_sequences: int
    sequences_flagged_as_poor_quality: int
    sequence_length: str
    pct_gc: int
    total_deduplicated_percentage: float
    avg_sequence_length: float

    basic_statistics: QCStatus
    per_base_sequence_quality: QCStatus
    per_tile_sequence_quality: QCStatus | None = Field(default=None)
    per_sequence_quality_scores: QCStatus
    per_base_sequence_content: QCStatus
    per_sequence_gc_content: QCStatus
    per_base_n_content: QCStatus
    sequence_length_distribution: QCStatus
    sequence_duplication_levels: QCStatus
    overrepresented_sequences: QCStatus
    adapter_content: QCStatus

    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Performs FastQC-specific data transformations
        """

        # Calculate unique and duplicate reads for each row (each fastq file)
        df["unique_reads"] = (
            (df["total_deduplicated_percentage"] / 100.0) * df["total_sequences"]
        ).astype(int)
        df["duplicate_reads"] = (df["total_sequences"] - df["unique_reads"]).astype(int)

        agg_df = (
            df.groupby("sample")
            .agg(
                total_unique_reads=("unique_reads", "sum"),
                total_duplicate_reads=("duplicate_reads", "sum"),
            )
            .reset_index()
        )
        df = pd.merge(df, agg_df, on="sample", how="left")

        # Drop the intermediate columns
        df = df.drop(columns=["unique_reads", "duplicate_reads"])

        # Coerce sequence_length to string to handle mixed types (e.g., '50-151' and 151)
        if "sequence_length" in df.columns:
            df["sequence_length"] = df["sequence_length"].astype(str)

        return df
