import json
from typing import TYPE_CHECKING, ClassVar

import pandas as pd
from sqlmodel import Field, Relationship

from ..utils import standardise_column_names
from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Run


class RunSummary(BaseMetrics, table=True):
    """Metrics from SAV InterOp RunSummary."""

    __tablename__ = "interop_runsummary"
    multiqc_section_names: ClassVar[list[str]] = ["interop_runsummary"]
    metric_level: ClassVar[str] = "run"

    sample_id: ClassVar[None] = None
    run_id: int | None = Field(
        default=None,
        foreign_key="run.id",
        description="Foreign key linking to the run",
    )
    run: "Run" = Relationship(back_populates="interop_runsummary_metrics")

    read: str

    yield_: float
    projected_yield: float
    aligned: float
    error_rate: float | None = Field(default=None)
    intensity_c1: int
    pct_q30: float
    pct_occupied: float
    
    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms InterOp RunSummary data by un-nesting the 'summary' JSON
        into multiple rows, one for each read type (e.g., 'Read 1', 'Total').
        """

        data = df.iloc[0]["summary"]

        df = pd.DataFrame.from_dict(data, orient="index")
        df = df.reset_index().rename(columns={"index": "read"})

        # The new df has raw column names (eg. 'Projected Yield', '%>=Q30').
        df = standardise_column_names(df)

        # Rename 'yield' to avoid a python keyword conflict.
        rename_map = {
            "yield": "yield_",
        }
        df = df.rename(columns=rename_map)

        return df


class IndexSummary(BaseMetrics, table=True):
    """Metrics from SAV InterOp IndexSummary, aggregated by lane."""

    __tablename__ = "interop_indexsummary"
    multiqc_section_names: ClassVar[list[str]] = ["interop_indexsummary"]
    metric_level: ClassVar[str] = "run"

    sample_id: ClassVar[None] = None
    run_id: int | None = Field(
        default=None,
        foreign_key="run.id",
        description="Foreign key linking to the run",
    )
    run: "Run" = Relationship(back_populates="interop_indexsummary_metrics")

    lane: str
    total_reads: int
    pf_reads: int
    pct_read_identified_pf: float
    cv: float
    min: float
    max: float
    
    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms InterOp IndexSummary data by un-nesting the 'summary' JSON
        into multiple rows, one for each lane.
        """
        data = df.iloc[0]["summary"]

        df = pd.DataFrame.from_dict(data, orient="index")
        df = df.reset_index().rename(columns={"index": "lane"})

        # Standardise the new column names (eg. 'PF Reads' -> 'pf_reads')
        df = standardise_column_names(df)

        return df
