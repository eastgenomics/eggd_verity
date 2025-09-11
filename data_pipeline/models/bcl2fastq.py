from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Field, Relationship

from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Sample


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

