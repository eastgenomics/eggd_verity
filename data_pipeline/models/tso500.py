from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Field, Relationship

from .reports import BaseMetrics
from .choices import NullableBool

if TYPE_CHECKING:
    from .reports import Sample


class Tso500MetricsOutputDna(BaseMetrics, table=True):
    """Metrics from the TSO500 MetricsOutput DNA results."""

    __tablename__ = "tso500_metrics_output_dna"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_tso500_metricsoutput_dna"]

    sample: "Sample" = Relationship(back_populates="tso500_metrics_output_dna")

    completed_all_steps: bool
    failed_steps: str | None = Field(default=None)
    steps_not_executed: str | None = Field(default=None)
    contamination_score: float | None = Field(default=None)
    contamination_p_value: float | None = Field(default=None)
    median_insert_size_dna: float | None = Field(default=None)
    median_exon_coverage: float | None = Field(default=None)
    pct_exon_50x: float | None = Field(default=None)
    usable_msi_sites: float | None = Field(default=None)
    coverage_mad: float | None = Field(default=None)
    median_bin_count_cnv_target: float | None = Field(default=None)
    contamination_summary: NullableBool
