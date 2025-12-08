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

