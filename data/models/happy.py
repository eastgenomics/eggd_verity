from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Field, Relationship

from .reports import BaseMetrics
import logging
import pandas as pd

if TYPE_CHECKING:
    from .reports import Sample


class HappyIndel(BaseMetrics, table=True):
    """Metrics from Hap.py 'INDEL' results."""

    __tablename__ = "happy_indel"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_happy_indel_data"]
    index_col: ClassVar[str] = "sample_id"

    sample: "Sample" = Relationship(back_populates="happy_indel_metrics")

    filter_indel: str
    truth_total_indel: int
    truth_tp_indel: int
    truth_fn_indel: int
    query_total_indel: int
    query_fp_indel: int
    query_unk_indel: int
    fp_gt_indel: int
    metric_recall_indel: float
    metric_precision_indel: float
    metric_frac_na_indel: float
    metric_f1_score_indel: float | None = Field(default=None)
    truth_total_titv_ratio_indel: float | None = Field(default=None)
    query_total_titv_ratio_indel: float | None = Field(default=None)
    truth_total_het_hom_ratio_indel: float
    query_total_het_hom_ratio_indel: float | None = Field(default=None)


class HappySnp(BaseMetrics, table=True):
    """Metrics from Hap.py 'SNP' results."""

    __tablename__ = "happy_snp"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_happy_snp_data"]
    index_col: ClassVar[str] = "sample_id"

    sample: "Sample" = Relationship(back_populates="happy_snp_metrics")

    filter_snp: str
    truth_total_snp: int
    truth_tp_snp: int
    truth_fn_snp: int
    query_total_snp: int
    query_fp_snp: int
    query_unk_snp: int
    fp_gt_snp: int
    metric_recall_snp: float
    metric_precision_snp: float
    metric_frac_na_snp: float
    metric_f1_score_snp: float
    truth_total_titv_ratio_snp: float | None = Field(default=None)
    query_total_titv_ratio_snp: float | None = Field(default=None)
    truth_total_het_hom_ratio_snp: float
    query_total_het_hom_ratio_snp: float | None = Field(default=None)
