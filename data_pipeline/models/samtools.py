from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Field, Relationship

from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Sample


class SamtoolsFlagstat(BaseMetrics, table=True):
    """Metrics from the Samtools 'flagstat' tool."""

    __tablename__ = "samtools_flagstat"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_samtools_flagstat"]

    sample: "Sample" = Relationship(back_populates="samtools_flagstat_metrics")

    total_passed: int
    total_failed: int
    secondary_passed: int
    secondary_failed: int
    supplementary_passed: int
    supplementary_failed: int
    duplicates_passed: int
    duplicates_failed: int
    mapped_passed: int
    mapped_failed: int
    mapped_passed_pct: float
    mapped_failed_pct: float | None = Field(default=None)
    paired_in_sequencing_passed: int
    paired_in_sequencing_failed: int
    read1_passed: int
    read1_failed: int
    read2_passed: int
    read2_failed: int
    properly_paired_passed: int
    properly_paired_failed: int
    properly_paired_passed_pct: float | None = Field(default=None)
    properly_paired_failed_pct: float | None = Field(default=None)
    with_itself_and_mate_mapped_passed: int
    with_itself_and_mate_mapped_failed: int
    singletons_passed: int
    singletons_failed: int
    singletons_passed_pct: float | None = Field(default=None)
    singletons_failed_pct: float | None = Field(default=None)
    with_mate_mapped_to_a_different_chr_passed: int
    with_mate_mapped_to_a_different_chr_failed: int
    with_mate_mapped_to_a_different_chr_mapq_5_passed: int
    with_mate_mapped_to_a_different_chr_mapq_5_failed: int
    flagstat_total: int