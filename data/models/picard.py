from typing import TYPE_CHECKING, ClassVar

import pandas as pd
from sqlmodel import Field, Relationship

from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Sample


class PicardAlignmentSummaryMetrics(BaseMetrics, table=True):
    """Metrics from Picard's AlignmentSummaryMetrics."""

    __tablename__ = "picard_alignment_summary_metrics"
    multiqc_section_names: ClassVar[list[str]] = [
        "multiqc_picard_AlignmentSummaryMetrics"
    ]

    sample: "Sample" = Relationship(back_populates="picard_alignment_summary_metrics")

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
    pf_reads_improper_pairs: int | None = Field(default=None)
    pct_pf_reads_improper_pairs: float | None = Field(default=None)
    bad_cycles: int
    strand_balance: float
    pct_chimeras: float
    pct_adapter: float


class PicardBaseContent(BaseMetrics, table=True):
    """Metrics from Picard's CollectBaseContentMetrics."""

    __tablename__ = "picard_base_content"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_picard_baseContent"]

    sample: "Sample" = Relationship(back_populates="picard_base_content_metrics")
    
    flow_cell: str | None = Field(default=None, description="Flow cell (eg S5)")
    lane: str | None = Field(default=None, description="Sequencing lane (eg L001)")
    read_pair: str | None = Field(default=None, description="Read pair (eg R1, R2)")

    sum_pct_a: float
    sum_pct_c: float
    sum_pct_g: float
    sum_pct_t: float
    sum_pct_n: float
    cycle_count: int
    mean_pct_a: float
    mean_pct_c: float
    mean_pct_g: float
    mean_pct_t: float


class PicardDups(BaseMetrics, table=True):
    """Metrics from Picard's MarkDuplicates."""

    __tablename__ = "picard_dups"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_picard_dups"]

    sample: "Sample" = Relationship(back_populates="picard_dups_metrics")

    library: str
    unpaired_reads_examined: int
    read_pairs_examined: int
    secondary_or_supplementary_rds: int
    unmapped_reads: int
    unpaired_read_duplicates: int
    read_pair_duplicates: int
    read_pair_optical_duplicates: int
    percent_duplication: float
    estimated_library_size: int
    reads_in_duplicate_pairs: int | None = Field(default=None)
    reads_in_unique_pairs: int | None = Field(default=None)
    reads_in_unique_unpaired: int | None = Field(default=None)
    reads_in_duplicate_pairs_optical: int | None = Field(default=None)
    reads_in_duplicate_pairs_nonoptical: int | None = Field(default=None)
    reads_in_duplicate_unpaired: int | None = Field(default=None)
    reads_unmapped: int | None = Field(default=None)


class PicardGcBias(BaseMetrics, table=True):
    """Metrics from Picard's CollectGcBiasMetrics."""

    __tablename__ = "picard_gcbias"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_picard_gcbias"]

    sample: "Sample" = Relationship(back_populates="picard_gcbias_metrics")

    accumulation_level: str
    reads_used: str
    window_size: int
    total_clusters: int
    aligned_reads: int
    at_dropout: float
    gc_dropout: float
    gc_nc_0_19: float
    gc_nc_20_39: float
    gc_nc_40_59: float
    gc_nc_60_79: float
    gc_nc_80_100: float


class PicardHsMetrics(BaseMetrics, table=True):
    """Metrics from Picard's CollectHsMetrics for hybrid selection."""

    __tablename__ = "picard_hs_metrics"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_picard_HsMetrics"]

    sample: "Sample" = Relationship(back_populates="picard_hs_metrics")

    bait_set: str
    bait_territory: int
    bait_design_efficiency: int
    on_bait_bases: int
    near_bait_bases: int
    off_bait_bases: int
    pct_selected_bases: float
    pct_off_bait: float
    on_bait_vs_selected: float | None = Field(default=None)
    mean_bait_coverage: float
    pct_usable_bases_on_bait: float
    pct_usable_bases_on_target: float
    fold_enrichment: float
    hs_library_size: float | None = Field(default=None)
    hs_penalty_10x: float
    hs_penalty_20x: float
    hs_penalty_30x: float
    hs_penalty_40x: float
    hs_penalty_50x: float
    hs_penalty_100x: float
    target_territory: int
    genome_size: int
    total_reads: int
    pf_reads: int
    pf_bases: int
    pf_unique_reads: int
    pf_uq_reads_aligned: int
    pf_bases_aligned: int
    pf_uq_bases_aligned: int
    on_target_bases: int
    pct_pf_reads: float
    pct_pf_uq_reads: float
    pct_pf_uq_reads_aligned: float
    mean_target_coverage: float
    median_target_coverage: float
    max_target_coverage: int
    min_target_coverage: int
    zero_cvg_targets_pct: float
    pct_exc_dupe: float
    pct_exc_adapter: float
    pct_exc_mapq: float
    pct_exc_baseq: float
    pct_exc_overlap: float
    pct_exc_off_target: float
    fold_80_base_penalty: float | None = Field(default=None)
    pct_target_bases_1x: float
    pct_target_bases_2x: float
    pct_target_bases_10x: float
    pct_target_bases_20x: float
    pct_target_bases_30x: float
    pct_target_bases_40x: float
    pct_target_bases_50x: float
    pct_target_bases_100x: float
    at_dropout: float
    gc_dropout: float
    het_snp_sensitivity: float
    het_snp_q: int


class PicardInsertSize(BaseMetrics, table=True):
    """Metrics from Picard's CollectInsertSizeMetrics."""

    __tablename__ = "picard_insert_size"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_picard_insertSize"]
    index_col: ClassVar[str] = "sample_name"

    sample: "Sample" = Relationship(back_populates="picard_insert_size_metrics")

    median_insert_size: float
    mode_insert_size: float | None = Field(default=None)
    median_absolute_deviation: float
    min_insert_size: float
    max_insert_size: float
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
    width_of_95_percent: int | None = Field(default=None)  # ?Remove; almost always null
    width_of_99_percent: int


class PicardPcrMetrics(BaseMetrics, table=True):
    """Metrics from Picard's CollectPcrMetrics."""

    __tablename__ = "picard_pcr_metrics"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_picard_pcrmetrics"]

    sample: "Sample" = Relationship(back_populates="picard_pcr_metrics")

    custom_amplicon_set: str
    amplicon_territory: int
    on_amplicon_bases: int
    near_amplicon_bases: int
    off_amplicon_bases: int
    pct_amplified_bases: float
    pct_off_amplicon: float
    on_amplicon_vs_selected: float | None = Field(default=None)
    mean_amplicon_coverage: float
    fold_enrichment: float
    pf_selected_pairs: int
    pf_selected_unique_pairs: int
    on_target_from_pair_bases: int
    target_territory: int
    genome_size: int
    total_reads: int
    pf_reads: int
    pf_bases: int
    pf_unique_reads: int
    pf_uq_reads_aligned: int
    pf_bases_aligned: int
    pf_uq_bases_aligned: int
    on_target_bases: int
    pct_pf_reads: float
    pct_pf_uq_reads: float
    pct_pf_uq_reads_aligned: float
    mean_target_coverage: float
    median_target_coverage: int
    max_target_coverage: int
    min_target_coverage: int
    zero_cvg_targets_pct: float
    pct_exc_dupe: float
    pct_exc_adapter: float
    pct_exc_mapq: float
    pct_exc_baseq: float
    pct_exc_overlap: float
    pct_exc_off_target: float
    fold_80_base_penalty: float | None = Field(default=None)
    pct_target_bases_1x: float
    pct_target_bases_2x: float
    pct_target_bases_10x: float
    pct_target_bases_20x: float
    pct_target_bases_30x: float
    pct_target_bases_40x: float
    pct_target_bases_50x: float
    pct_target_bases_100x: float
    at_dropout: float
    gc_dropout: float
    het_snp_sensitivity: float
    het_snp_q: int


class PicardQualityYieldMetrics(BaseMetrics, table=True):
    """Metrics from Picard's QualityYieldMetrics."""

    __tablename__ = "picard_quality_yield_metrics"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_picard_QualityYieldMetrics"]

    sample: "Sample" = Relationship(back_populates="picard_quality_yield_metrics")

    total_reads: int
    pf_reads: int
    read_length: int
    total_bases: int
    pf_bases: int
    q20_bases: int
    pf_q20_bases: int
    q30_bases: int
    pf_q30_bases: int
    q20_equivalent_yield: int
    pf_q20_equivalent_yield: int


class PicardVariantCalling(BaseMetrics, table=True):
    """Metrics from Picard's VariantCallingMetrics."""

    __tablename__ = "picard_variant_calling"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_picard_variantCalling"]

    sample: "Sample" = Relationship(back_populates="picard_variant_calling_metrics")

    het_homvar_ratio: float | None = Field(default=None)
    pct_gq0_variants: float | None = Field(default=None)
    total_gq0_variants: int
    total_het_depth: int
    total_snps: int
    num_in_db_snp: int
    novel_snps: int
    filtered_snps: int
    pct_dbsnp: float | None = Field(default=None)
    dbsnp_titv: float
    novel_titv: float
    total_indels: int
    novel_indels: int
    filtered_indels: int
    pct_dbsnp_indels: float | None = Field(default=None)
    num_in_db_snp_indels: int
    dbsnp_ins_del_ratio: float
    novel_ins_del_ratio: float
    total_multiallelic_snps: int
    num_in_db_snp_multiallelic: int
    total_complex_indels: int
    num_in_db_snp_complex_indels: int
    snp_reference_bias: float | None = Field(default=None)
    num_singletons: int
    total_called_variants: int
    total_called_variants_known: int
    total_called_variants_novel: int


class PicardRnaSeqMetrics(BaseMetrics, table=True):
    """Metrics from Picard's CollectRnaSeqMetrics."""

    __tablename__ = "picard_rnaseq_metrics"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_picard_RnaSeqMetrics"]

    sample: "Sample" = Relationship(back_populates="picard_rnaseq_metrics")

    pf_bases: int
    pf_aligned_bases: int
    coding_bases: int
    utr_bases: int
    intronic_bases: int
    intergenic_bases: int
    ignored_reads: int
    correct_strand_reads: int
    incorrect_strand_reads: int
    num_r1_transcript_strand_reads: int
    num_r2_transcript_strand_reads: int
    num_unexplained_reads: int
    pct_r1_transcript_strand_reads: float
    pct_r2_transcript_strand_reads: float
    pct_coding_bases: float
    pct_utr_bases: float
    pct_intronic_bases: float
    pct_intergenic_bases: float
    pct_mrna_bases: float
    pct_usable_bases: float
    pct_correct_strand_reads: float
    median_cv_coverage: float
    median_5prime_bias: float
    median_3prime_bias: float
    median_5prime_to_3prime_bias: float
    pf_not_aligned_bases: int
    
    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Strips '.star' suffix from sample names."""
        if "sample" in df.columns and df["sample"].str.contains(".star").any():
            df["sample"] = df["sample"].str.replace(".star", "", regex=False)

        return df
