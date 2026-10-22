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
            plot_type="box",
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

    def test_runs_on_x_axis_in_date_order(self):
        """Runs are x axis categories in date order, with slanted labels."""
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
                "run_folder": ["run_b", "run_a", "run_c"],
                "sample_name": ["s1", "s2", "s3"],
                "my_metric": [10, 20, 30],
                # The first trace only covers the later run
                "group": ["B", "A", "B"],
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

        assert list(fig.layout.xaxis.categoryarray) == ["run_b", "run_a", "run_c"]
        assert fig.layout.xaxis.tickangle == -45
        assert fig.layout.xaxis.title.text == "Run"
        # The caller's DataFrame is not changed
        assert "my_metric" in df.columns

    def test_box_plot_is_notched_and_ignores_symbol(self):
        """Box plots are notched, show points, and drop the symbol grouping."""
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01"] * 3 + ["2023-01-02"] * 3),
                "run_folder": ["run1"] * 3 + ["run2"] * 3,
                "sample_name": [f"s{i}" for i in range(6)],
                "my_metric": [10, 11, 12, 20, 21, 22],
                "sym": ["x", "y", "x", "y", "x", "y"],
            }
        )

        fig = create_trends_figure(
            df=df,
            tool_name="Test Tool",
            metric_names=["my_metric"],
            plot_type="box",
            color_col=None,
            symbol_col="sym",
            yaxis_transform="linear",
            show_stats=[],
            marker_size=10,
            is_run_level=False,
        )

        assert all(trace.type == "box" for trace in fig.data)
        assert all(trace.notched for trace in fig.data)
        assert all(trace.boxpoints == "all" for trace in fig.data)
