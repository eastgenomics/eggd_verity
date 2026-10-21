from typing import TYPE_CHECKING, ClassVar

import pandas as pd
from sqlmodel import Field, Relationship

from .reports import BaseMetrics

if TYPE_CHECKING:
    from .reports import Sample


class GenStats(BaseMetrics, table=True):
    """Selected custom metrics from general stats table."""

    __tablename__ = "gen_stats"
    multiqc_section_names: ClassVar[list[str]] = ["multiqc_general_stats"]

    sample: "Sample" = Relationship(back_populates="gen_stats_metrics")

    custom_coverage_250x: float | None = Field(default=None)
    custom_coverage_500x: float | None = Field(default=None)
    custom_coverage_1000x: float | None = Field(default=None)
    custom_coverage_usable_unique_bases_on_target: float | None = Field(default=None)

    @classmethod
    def custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        rename custom metrics
        """
        alias_mapping = {
            "custom_content_custom_coverage_250x": "custom_coverage_250x",
            "custom_content_custom_coverage_500x": "custom_coverage_500x",
            "custom_content_custom_coverage_1000x": "custom_coverage_1000x",
            "custom_content_custom_coverage_usable_unique_bases_on_target": "custom_coverage_usable_unique_bases_on_target",
        }

        df = df.rename(columns=alias_mapping)

        return df
