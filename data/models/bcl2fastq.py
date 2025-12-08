import json
from typing import TYPE_CHECKING, ClassVar

import pandas as pd
from sqlalchemy import JSON
from sqlmodel import Column, Field, Relationship

from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Run, Sample


class Bcl2fastqBySample(BaseMetrics, table=True):
    """Metrics from the bcl2fastq tool, aggregated by sample."""

    __tablename__ = "bcl2fastq_bysample"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_bcl2fastq_bysample"]

    sample: "Sample" = Relationship(back_populates="bcl2fastq_bysample_metrics")

    total: int
    total_yield: int
    perfectindex: int
    yieldq30: int
    qscore_sum: int
    r1_yield: int | None = Field(default=None)
    r1_q30: int | None = Field(default=None)
    r1_trimmed_bases: int | None = Field(default=None)
    r2_yield: int | None = Field(default=None)
    r2_q30: int | None = Field(default=None)
    r2_trimmed_bases: int | None = Field(default=None)
    percent_q30: float | None = Field(default=None)
    percent_perfectindex: float | None = Field(default=None)
    mean_qscore: float | None = Field(default=None)


class Bcl2fastqByLane(BaseMetrics, table=True):
    """Metrics from the bcl2fastq tool, aggregated by lane."""

    __tablename__ = "bcl2fastq_bylane"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_bcl2fastq_bylane"]
    index_col: ClassVar[str] = "lane"
    metric_level: ClassVar[str] = "run"

    sample_id: ClassVar[None] = None
    run_id: int = Field(foreign_key="run.id")
    run: "Run" = Relationship(back_populates="bcl2fastq_bylane_metrics")

    lane: str
    total: int
    total_yield: int
    perfectindex: int
    undetermined: int
    yieldq30: int
    qscore_sum: int
    percent_q30: float
    percent_perfectindex: float
    mean_qscore: float
    unknown_barcodes: dict[str, int] | None = Field(
        default=None, sa_column=Column(JSON)
    )
    
    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename 'sample' to 'lane' and clean it
        """
        
        if "sample" in df.columns:
            df = df.rename(columns={"sample": "lane"})
            # Extracts 'L1' from 'RUN_ID - L1' or similar
            df["lane"] = df["lane"].str.split(" - ").str[-1]

        return df
