import pandas as pd
import plotly.graph_objects as go

from data.plots.correlation import create_correlation_figure


class TestCorrelationPlot:
    def test_create_correlation_figure(self):
        """Tests creating a standard correlation figure."""
        df = pd.DataFrame(
            {
                "x": [1, 2, 3],
                "y": [2, 4, 6],
                "sample_name": ["s1", "s2", "s3"],
                "run_folder": ["r1", "r1", "r1"],
                "group": ["A", "A", "B"],
            }
        )

        fig = create_correlation_figure(
            df=df,
            x_metric="metric_x",
            y_metric="metric_y",
            color_col="group",
            symbol_col=None,
            marker_size=10,
            trendline="none",
            xaxis_transform="linear",
            yaxis_transform="linear",
        )

        assert isinstance(fig, go.Figure)
        assert "Correlation: Metric X vs. Metric Y" in fig.layout.title.text

    def test_create_correlation_figure_empty_after_log(self):
        """
        Tests that a warning figure is returned if log transform removes all data.
        """
        df = pd.DataFrame(
            {
                "x": [-1, 0, -3],
                "y": [2, 4, 6],
                "sample_name": ["s1", "s2", "s3"],
                "run_folder": ["r1", "r1", "r1"],
            }
        )

        fig = create_correlation_figure(
            df=df,
            x_metric="metric_x",
            y_metric="metric_y",
            color_col=None,
            symbol_col=None,
            marker_size=10,
            trendline="none",
            xaxis_transform="log",  # This will filter out all data
            yaxis_transform="linear",
        )

        assert isinstance(fig, go.Figure)
        # Check that axes are hidden and annotation is present
        assert fig.layout.xaxis.visible is False
        assert "No data points remain" in fig.layout.annotations[0].text
