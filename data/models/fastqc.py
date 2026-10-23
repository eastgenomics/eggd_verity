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
    per_fastq: ClassVar[bool] = True

    sample: "Sample" = Relationship(back_populates="fastqc_metrics")

    lane: str | None = Field(default=None, description="Sequencing lane (eg L001)")
    read_pair: str | None = Field(default=None, description="Read pair (eg R1, R2)")

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

        # Coerce sequence_length to string to handle mixed types (e.g., '50-151' and 151)
        if "sequence_length" in df.columns:
            df["sequence_length"] = df["sequence_length"].astype(str)

        return df
