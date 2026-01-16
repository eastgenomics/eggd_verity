import pandas as pd
import plotly.graph_objects as go

from data.plots.raincloud import create_raincloud_figure


class TestRaincloudPlot:
    def test_create_raincloud_figure(self):
        """Tests creating a standard raincloud figure."""
        df = pd.DataFrame(
            {
                "run_folder": ["run1", "run1", "run2", "run2"],
                "metric_val": [10, 12, 20, 22],
                "sample_name": ["s1", "s2", "s3", "s4"],
                "group": ["A", "A", "B", "B"],
            }
        )

        fig = create_raincloud_figure(
            df=df,
            tool_name="Test Tool",
            metric_name="metric_val",
            num_runs=2,
            color_col="group",
            violin_side="positive",
            plot_components=["violin", "box", "points"],
        )

        assert isinstance(fig, go.Figure)
        assert "Test Tool: Metric Val" in fig.layout.title.text
