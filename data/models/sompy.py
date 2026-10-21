from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Field, Relationship

from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Sample


class Sompy(BaseMetrics, table=True):
    """Metrics from the Som.py tool."""

    __tablename__ = "sompy"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_sompy"]

    sample: "Sample" = Relationship(back_populates="sompy_metrics")

    indels_total_truth: int
    indels_total_query: int
    indels_tp: int
    indels_fp: int
    indels_fn: int
    indels_unk: int
    indels_ambi: int
    indels_recall: float
    indels_recall_lower: float
    indels_recall_upper: int
    indels_recall2: float
    indels_precision: float
    indels_precision_lower: float
    indels_precision_upper: float
    indels_na: float
    indels_ambiguous: int
    indels_fp_region_size: int
    indels_fp_rate: float

    snvs_total_truth: int
    snvs_total_query: int
    snvs_tp: int
    snvs_fp: int
    snvs_fn: int
    snvs_unk: int
    snvs_ambi: int
    snvs_recall: float
    snvs_recall_lower: float
    snvs_recall_upper: float
    snvs_recall2: float
    snvs_precision: float
    snvs_precision_lower: float
    snvs_precision_upper: float
    snvs_na: float
    snvs_ambiguous: int
    snvs_fp_region_size: int
    snvs_fp_rate: float

    records_total_truth: int
    records_total_query: int
    records_tp: int
    records_fp: int
    records_fn: int
    records_unk: int
    records_ambi: int
    records_recall: float
    records_recall_lower: float
    records_recall_upper: float
    records_recall2: float
    records_precision: float
    records_precision_lower: float
    records_precision_upper: float
    records_na: float
    records_ambiguous: int
    records_fp_region_size: int
    records_fp_rate: float


class SompyCombined(BaseMetrics, table=True):
    """Combined Som.py metrics."""

    __tablename__ = "sompy_combined"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_sompy_combined_data"]
    index_col: ClassVar[str] = "sample_id"

    sample: "Sample" = Relationship(back_populates="sompy_combined_metrics")

    total_truth_combined: int
    total_query_combined: int
    tp_combined: int
    fp_combined: int
    fn_combined: int
    unk_combined: int
    ambi_combined: int
    recall_combined: float
    recall_lower_combined: float
    recall_upper_combined: float
    recall2_combined: float
    precision_combined: float
    precision_lower_combined: float
    precision_upper_combined: float
    na_combined: float
    ambiguous_combined: float
    fp_region_size_combined: float
    fp_rate_combined: float


class SompyIndel(BaseMetrics, table=True):
    """Indel Som.py metrics."""

    __tablename__ = "sompy_indel"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_sompy_indel_data"]
    index_col: ClassVar[str] = "sample_id"

    sample: "Sample" = Relationship(back_populates="sompy_indel_metrics")

    total_truth_indel: int
    total_query_indel: int
    tp_indel: int
    fp_indel: int
    fn_indel: int
    unk_indel: int
    ambi_indel: int
    recall_indel: float
    recall_lower_indel: float
    recall_upper_indel: float
    recall2_indel: float
    precision_indel: float
    precision_lower_indel: float
    precision_upper_indel: float
    na_indel: float
    ambiguous_indel: float
    fp_region_size_indel: float
    fp_rate_indel: float


class SompySnv(BaseMetrics, table=True):
    """SNV Som.py metrics."""

    __tablename__ = "somp_snv"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_sompy_snv_data"]
    index_col: ClassVar[str] = "sample_id"

    sample: "Sample" = Relationship(back_populates="sompy_snv_metrics")

    total_truth_snv: int
    total_query_snv: int
    tp_snv: int
    fp_snv: int
    fn_snv: int
    unk_snv: int
    ambi_snv: int
    recall_snv: float
    recall_lower_snv: float
    recall_upper_snv: float
    recall2_snv: float
    precision_snv: float
    precision_lower_snv: float
    precision_upper_snv: float
    na_snv: float
    ambiguous_snv: float
    fp_region_size_snv: float
    fp_rate_snv: float
