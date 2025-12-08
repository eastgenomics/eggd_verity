from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Field, Relationship

from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Sample


class SentieonAlignmentSummaryMetrics(BaseMetrics, table=True):
    """Metrics from Sentieon's AlignmentSummaryMetrics."""

    __tablename__ = "sentieon_alignment_summary_metrics"
    multiqc_section_names: ClassVar[list[str]] = [
        "multiqc_sentieon_AlignmentSummaryMetrics"
    ]

    sample: "Sample" = Relationship(back_populates="sentieon_alignment_summary_metrics")

    category: str
    total_reads: int
    pf_reads: int
    pct_pf_reads: float
    pf_noise_reads: int
    pf_reads_aligned: int
    pct_pf_reads_aligned: float
    pf_aligned_bases: int
    pf_hq_aligned_reads: int
    pf_hq_aligned_bases: int
    pf_hq_aligned_q20_bases: int
    pf_hq_median_mismatches: float
    pf_mismatch_rate: float
    pf_hq_error_rate: float
    pf_indel_rate: float
    mean_read_length: float
    reads_aligned_in_pairs: int
    pct_reads_aligned_in_pairs: float
    bad_cycles: int
    strand_balance: float
    pct_chimeras: float
    pct_adapter: float


class SentieonInsertSize(BaseMetrics, table=True):
    """Metrics from Sentieon's CollectInsertSizeMetrics."""

    __tablename__ = "sentieon_insert_size"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_sentieon_insertSize"]
    index_col: ClassVar[str] = "sample_name"

    sample: "Sample" = Relationship(back_populates="sentieon_insert_size_metrics")

    median_insert_size: int
    median_absolute_deviation: float
    min_insert_size: int
    max_insert_size: int
    mean_insert_size: float
    standard_deviation: float | None = Field(default=None)
    read_pairs: int
    pair_orientation: str
    width_of_10_percent: int
    width_of_20_percent: int
    width_of_30_percent: int
    width_of_40_percent: int
    width_of_50_percent: int
    width_of_60_percent: int
    width_of_70_percent: int
    width_of_80_percent: int
    width_of_90_percent: int
    width_of_99_percent: int
