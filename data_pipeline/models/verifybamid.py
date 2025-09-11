from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Field, Relationship

from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Sample


class VerifyBamId(BaseMetrics, table=True):
    """Metrics from the VerifyBAMID tool for contamination checks."""

    __tablename__ = "verifybamid"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_verifybamid"]

    sample: "Sample" = Relationship(back_populates="verifybamid_metrics")

    rg: str
    snps: int
    reads: int
    avg_dp: float
    freemix: float
    freelk1: float
    freelk0: float
