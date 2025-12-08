from typing import TYPE_CHECKING, ClassVar

import pandas as pd
from sqlmodel import Field, Relationship

from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Sample


class RnaSeqc(BaseMetrics, table=True):
    """Metrics from the RNA-SeQC tool."""

    __tablename__ = "rna_seqc"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_rna_seqc"]

    sample: "Sample" = Relationship(back_populates="rna_seqc_metrics")

    mapping_rate: float
    unique_rate_of_mapped: int
    duplicate_rate_of_mapped: int
    duplicate_rate_of_mapped_excluding_globins: int
    base_mismatch: float
    end_1_mapping_rate: float
    end_2_mapping_rate: float
    end_1_mismatch_rate: float | None = Field(default=None)
    end_2_mismatch_rate: float | None = Field(default=None)
    expression_profiling_efficiency: float
    high_quality_rate: float
    exonic_rate: float
    intronic_rate: float
    intergenic_rate: float
    intragenic_rate: float
    ambiguous_alignment_rate: float
    high_quality_exonic_rate: float
    high_quality_intronic_rate: float
    high_quality_intergenic_rate: float
    high_quality_intragenic_rate: float
    high_quality_ambiguous_alignment_rate: float
    discard_rate: int
    rrna_rate: float
    end_1_sense_rate: float
    end_2_sense_rate: float
    avg_splits_per_read: float
    alternative_alignments: int
    duplicate_reads: int
    chimeric_reads: int
    chimeric_alignment_rate: float
    end_1_antisense: int
    end_2_antisense: int
    end_1_bases: int
    end_2_bases: int
    end_1_mapped_reads: int
    end_2_mapped_reads: int
    end_1_mismatches: int
    end_2_mismatches: int
    end_1_sense: int
    end_2_sense: int
    exonic_reads: int
    failed_vendor_qc: int
    high_quality_reads: int
    intergenic_reads: int
    intragenic_reads: int
    ambiguous_reads: int
    intronic_reads: int
    low_mapping_quality: int
    low_quality_reads: int
    mapped_duplicate_reads: int
    mapped_reads: int
    mapped_unique_reads: int
    mismatched_bases: int
    non_globin_reads: int
    non_globin_duplicate_reads: int
    reads_used_for_intron_exon_counts: int
    rrna_reads: int
    total_bases: int
    total_mapped_pairs: int
    total_read_number: int
    unique_mapping_vendor_qc_passed_reads: int
    unpaired_reads: int
    read_length: int
    genes_detected: int
    estimated_library_complexity: int
    genes_used_in_3_bias: int
    mean_3_bias: float
    median_3_bias: float
    three_prime_bias_std: float
    three_prime_bias_mad_std: float
    three_prime_bias_25th_percentile: float
    three_prime_bias_75th_percentile: float
    average_fragment_length: float | None = Field(default=None)
    fragment_length_median: float | None = Field(default=None)
    fragment_length_std: float | None = Field(default=None)
    fragment_length_mad_std: float | None = Field(default=None)
    median_of_avg_transcript_coverage: float
    median_of_transcript_coverage_std: float
    median_of_transcript_coverage_cv: float
    median_exon_cv: float
    exon_cv_mad: float
    
    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handles RNA-SeQC specific transformations:
        - Renames columns that start with a number.
        - Strips '.star' suffix from sample names.
        """
        alias_mapping = {
            "3_bias_std": "three_prime_bias_std",
            "3_bias_mad_std": "three_prime_bias_mad_std",
            "3_bias_25th_percentile": "three_prime_bias_25th_percentile",
            "3_bias_75th_percentile": "three_prime_bias_75th_percentile",
        }
        df = df.rename(columns=alias_mapping)

        if "sample" in df.columns and df["sample"].str.contains(".star").any():
            df["sample"] = df["sample"].str.replace(".star", "", regex=False)

        return df

