import json
from typing import TYPE_CHECKING, ClassVar

import pandas as pd
from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship

from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Run, Sample


class BclconvertBySample(BaseMetrics, table=True):
    """Metrics from the bclconvert tool, aggregated by sample."""

    __tablename__ = "bclconvert_bysample"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_bclconvert_bysample"]
    index_col: ClassVar[str] = "level_0"

    sample: "Sample" = Relationship(back_populates="bclconvert_bysample_metrics")

    cluster_length: int
    clusters: int
    perfect_index_reads: int
    one_mismatch_index_reads: int
    percent_clusters: float
    percent_perfect_index_reads: float
    percent_one_mismatch_index_reads: float
    total_yield: int
    percent_yield: float
    yield_q30: int
    percent_yield_q30: float
    mean_quality: float
    calculated_yield: int
    
    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename col names to match db names and avoid sample conflict.
        """
        alias_mapping = {
            "sample": "index",
            "yield": "total_yield",
        }
        df = df.rename(columns=alias_mapping)

        return df


class BclconvertByLane(BaseMetrics, table=True):
    """Metrics from the bclconvert tool, aggregated by lane."""

    __tablename__ = "bclconvert_bylane"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_bclconvert_bylane"]
    index_col: ClassVar[str] = "lane"
    sample_id: ClassVar[None] = None
    
    metric_level: ClassVar[str] = "run"
   
    run_id: int = Field(foreign_key="run.id")
    run: "Run" = Relationship(back_populates="bclconvert_bylane_metrics")

    lane: str
    cluster_length: int
    clusters: int
    perfect_index_reads: int
    one_mismatch_index_reads: int
    percent_clusters: float
    percent_perfect_index_reads: float
    percent_one_mismatch_index_reads: float
    total_yield: int
    percent_yield: float
    yield_q30: int
    percent_yield_q30: float
    mean_quality: float
    calculated_yield: int
    top_unknown_barcodes: dict | None = Field(default=None, sa_column=Column(JSON))
    
    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename cols to match db; clean lane names.
        """
        alias_mapping = {
            "sample": "lane",
            "yield": "total_yield",
        }
        df = df.rename(columns=alias_mapping)

        df["lane"] = df["lane"].str.split(" - ").str[-1]

        # Drop the redundant 'samples' column
        if "samples" in df.columns:
            df = df.drop(columns=["samples"])

        return df

