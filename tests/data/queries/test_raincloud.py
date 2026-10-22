from datetime import datetime

from sqlmodel import Session

from data.models.samtools import SamtoolsFlagstat
from data.queries.raincloud import get_raincloud_data
from tests.data.queries.test_trends import _setup_runs


class TestRaincloudQueries:
    def test_latest_runs_with_data(self, session: Session):
        """Only the newest runs that have a value for the metric are returned."""
        _setup_runs(
            session,
            [datetime(2023, 1, d) for d in (1, 2, 3, 4)],
            [True, True, True, False],
        )
        df, grouping = get_raincloud_data(
            session,
            assay_names=["Multi Assay"],
            tool_model=SamtoolsFlagstat,
            metric_name="mapped_failed_pct",
            num_runs=2,
            color_by="run.sequencer_id",
        )

        assert list(df["run_folder"]) == ["run_1", "run_2"]
        assert grouping == {"color": "run_sequencer_id"}

    def test_no_run_limit_returns_all_runs(self, session: Session):
        """An empty run count returns every run with data."""
        _setup_runs(
            session,
            [datetime(2023, 1, d) for d in (1, 2, 3)],
            [True, True, True],
        )
        df, _ = get_raincloud_data(
            session,
            assay_names=["Multi Assay"],
            tool_model=SamtoolsFlagstat,
            metric_name="mapped_failed_pct",
            num_runs=None,
            color_by=None,
        )

        assert list(df["run_folder"]) == ["run_0", "run_1", "run_2"]
