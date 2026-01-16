import pandas as pd
import plotly.graph_objects as go

from data.plots.trends import create_trends_figure


class TestTrendsPlot:
    def test_create_trends_figure_single_metric(self):
        """Tests creating a trends figure for a single metric."""
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
                "run_folder": ["run1", "run2"],
                "sample_name": ["s1", "s2"],
                "my_metric": [10, 20],
                "group": ["A", "B"],
            }
        )

        fig = create_trends_figure(
            df=df,
            tool_name="Test Tool",
            metric_names=["my_metric"],
            plot_type="scatter",
            color_col="group",
            symbol_col=None,
            yaxis_transform="linear",
            show_stats=[],
            marker_size=10,
            is_run_level=False,
        )

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Trend for Test Tool: My Metric"
        assert len(fig.data) > 0

    def test_create_trends_figure_multi_metric(self):
        """Tests creating a trends figure for multiple metrics (z-score)."""
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
                "run_folder": ["run1", "run2"],
                "sample_name": ["s1", "s2"],
                "m1": [10, 20],
                "m2": [5, 15],
            }
        )

        fig = create_trends_figure(
            df=df,
            tool_name="Test Tool",
            metric_names=["m1", "m2"],
            plot_type="line",
            color_col=None,
            symbol_col=None,
            yaxis_transform="standardise",  # This is forced for multi-metric
            show_stats=[],
            marker_size=10,
            is_run_level=False,
        )

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Trends for Test Tool"
        assert "Z-score" in fig.layout.yaxis.title.text
