from typing import TYPE_CHECKING, ClassVar

from sqlmodel import Field, Relationship

from .reports import BaseMetrics
from .choices import SexKaryotype, NullableBool

if TYPE_CHECKING:
    from .reports import Sample


class SomalierSexCheck(BaseMetrics, table=True):
    """Metrics from Somalier's sex check tool."""

    __tablename__ = "somalier_sex_check"
    multiqc_section_names: ClassVar[list[str]] = [
        "multiqc_somalier_sex_check",
        "multiqc_somalier_table",
    ]

    sample: "Sample" = Relationship(back_populates="somalier_sex_check_metrics")

    paternal_id: int
    maternal_id: int
    family_id: str
    sex: SexKaryotype
    phenotype: int
    original_pedigree_sex: SexKaryotype
    gt_depth_mean: float
    gt_depth_sd: float | None = Field(default=None)
    depth_mean: float
    depth_sd: float
    ab_mean: float
    ab_std: float | None = Field(default=None)
    n_hom_ref: int
    n_het: int
    n_hom_alt: int
    n_unknown: int
    p_middling_ab: float
    x_depth_mean: float
    x_n: int
    x_hom_ref: int
    x_het: int
    x_hom_alt: int
    y_depth_mean: float
    y_n: int
    predicted_sex: SexKaryotype
    match_sexes: NullableBool = Field(default=None)
