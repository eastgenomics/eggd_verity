import pandas as pd
import plotly.graph_objects as go

from data.plots.trends import create_trends_figure


class TestTrendsPlot:
    def test_create_trends_figure_single_metric(self):
        """Tests creating a trends figure for a single metric."""
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
                "project_name": ["run1", "run2"],
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
                "project_name": ["run1", "run2"],
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
                "project_name": ["run_b", "run_a", "run_c"],
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
                "project_name": ["run1"] * 3 + ["run2"] * 3,
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

    def test_long_run_names_are_truncated_on_the_axis(self):
        """Tick labels drop the 002_ prefix and are shortened; the full name stays the category."""
        long_run = "002_260920_A01295_0853_BHTVNLDRX7_CEN38"
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01"]),
                "project_name": [long_run],
                "sample_name": ["s1"],
                "my_metric": [10],
            }
        )

        fig = create_trends_figure(
            df=df,
            tool_name="Test Tool",
            metric_names=["my_metric"],
            plot_type="scatter",
            color_col=None,
            symbol_col=None,
            yaxis_transform="linear",
            show_stats=["show_stats"],
            marker_size=10,
            is_run_level=False,
        )

        assert list(fig.layout.xaxis.tickvals) == [long_run]
        assert fig.layout.xaxis.ticktext[0] == "260920_A01295_0853_…"
        assert fig.data[0].x[0] == long_run
        assert all(shape.line.width == 1 for shape in fig.layout.shapes)

    def test_hover_carries_sample_count_per_run(self):
        """Samples stacked on one value are still counted for their run."""
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01"] * 3 + ["2023-01-02"]),
                "project_name": ["run1", "run1", "run1", "run2"],
                "sample_name": ["s1", "s2", "s3", "s4"],
                "my_metric": [100.0, 100.0, 100.0, 90.0],
            }
        )
        kwargs = dict(
            tool_name="Test Tool",
            metric_names=["my_metric"],
            plot_type="scatter",
            color_col=None,
            symbol_col=None,
            yaxis_transform="linear",
            show_stats=[],
            marker_size=10,
        )

        fig = create_trends_figure(df=df, is_run_level=False, **kwargs)
        assert [row[2] for row in fig.data[0].customdata] == [3, 3, 3, 1]
        assert "Samples in run" in fig.data[0].hovertemplate

        run_df = df.drop(columns="sample_name")
        fig = create_trends_figure(df=run_df, is_run_level=True, **kwargs)
        assert all(row[2] is None for row in fig.data[0].customdata)
        assert "Samples in run" not in fig.data[0].hovertemplate
