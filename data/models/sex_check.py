from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Field, Relationship

from .reports import BaseMetrics
from .choices import SexKaryotype, NullableBool

if TYPE_CHECKING:
    from .reports import Sample


class SexCheck(BaseMetrics, table=True):
    """Metrics from eggd_sex_check."""

    __tablename__ = "sex_check"
    multiqc_section_names: ClassVar[list[str]] = [
        "multiqc_sex_check",
        "multiqc_sex_check_table",
    ]

    sample: "Sample" = Relationship(back_populates="sex_check_metrics")

    matched: NullableBool = Field(default=None)
    reported_sex: SexKaryotype
    predicted_sex: SexKaryotype
    score: float
    mapped_chry: int
    mapped_chr1: int
