from typing import TYPE_CHECKING, ClassVar

import pandas as pd
from sqlmodel import Field, Relationship

from .choices import SexKaryotype
from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Sample


class VcfQcHetHom(BaseMetrics, table=True):
    """Metrics from vcf_qc for het/hom ratio analysis."""

    __tablename__ = "vcfqc_hethom"
    multiqc_section_names: ClassVar[list[str]] = [
        "multiqc_het-hom_analysis",
        "multiqc_het-hom_table",
    ]
    run_id: ClassVar[None] = None

    sample: "Sample" = Relationship(back_populates="vcfqc_hethom_metrics")

    mean_het: float
    mean_hom: float
    het_hom_ratio: float
    x_het_hom_ratio: float
    gender: SexKaryotype = Field(default=SexKaryotype.UNKNOWN)

    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Handles aliases and coerces numeric columns to float, filling NA with 0."""
        # Alias field is broken in SQLModel v0.0.14
        # https://github.com/fastapi/sqlmodel/discussions/725
        # But this workaround is perfect for `bulk_create_from_df`

        alias_mapping = {
            "mean_het_ratio": "mean_het",
            "mean_homo_ratio": "mean_hom",
            "het_homo_ratio": "het_hom_ratio",
            "x_homo_het_ratio": "x_het_hom_ratio",
        }

        df = df.rename(columns=alias_mapping)

        for col in alias_mapping.values():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df
