import pandas as pd
import plotly.graph_objects as go

from data.plots.raincloud import create_raincloud_figure


def _legend_names(fig):
    return [trace.name for trace in fig.data if trace.showlegend is not False]


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

    def test_run_level_colour_shows_one_legend_entry_per_category(self):
        """A colour that is constant per run (e.g. sequencer) gets a legend."""
        df = pd.DataFrame(
            {
                "run_folder": ["run1", "run1", "run2", "run2", "run3", "run3"],
                "metric_val": [10, 12, 20, 22, 30, 32],
                "sample_name": [f"s{i}" for i in range(6)],
                "run_sequencer_id": ["seqA", "seqA", "seqB", "seqB", "seqA", "seqA"],
            }
        )

        fig = create_raincloud_figure(
            df=df,
            tool_name="Test Tool",
            metric_name="metric_val",
            num_runs=3,
            color_col="run_sequencer_id",
            violin_side="positive",
            plot_components=["violin", "box", "points"],
            color_label="Run: Sequencer Id",
        )

        assert fig.layout.showlegend
        assert sorted(_legend_names(fig)) == ["seqA", "seqB"]
        assert fig.layout.legend.title.text == "Run: Sequencer Id"
        violins = [t for t in fig.data if t.type == "violin"]
        assert violins[0].line.color == violins[2].line.color
        assert violins[0].line.color != violins[1].line.color

    def test_sample_level_colour_colours_each_sample(self):
        """A colour that varies within a run colours the points, not the run."""
        df = pd.DataFrame(
            {
                "run_folder": ["run1", "run1", "run2", "run2"],
                "metric_val": [10, 12, 20, 22],
                "sample_name": ["s1", "s2", "s3", "s4"],
                "sample_sex": ["Male", "Female", "Male", None],
            }
        )

        fig = create_raincloud_figure(
            df=df,
            tool_name="Test Tool",
            metric_name="metric_val",
            num_runs=2,
            color_col="sample_sex",
            violin_side="positive",
            plot_components=["violin", "points"],
        )

        points = [t for t in fig.data if t.type == "box"]
        # run1: Male, Female; run2: Male, N/A
        assert [(t.x[0], t.name) for t in points] == [
            ("run1", "Male"),
            ("run1", "Female"),
            ("run2", "Male"),
            ("run2", "N/A"),
        ]
        assert points[0].marker.color == points[2].marker.color
        assert sorted(_legend_names(fig)) == ["Female", "Male", "N/A"]
        # Violins use one neutral colour and stay out of the legend
        violins = [t for t in fig.data if t.type == "violin"]
        assert len({v.line.color for v in violins}) == 1
        assert not any(v.showlegend for v in violins)

    def test_colours_cycle_past_palette_length(self):
        """More runs than palette colours still gives every run a colour."""
        runs = [f"run{i:02d}" for i in range(12)]
        df = pd.DataFrame(
            {
                "run_folder": runs,
                "metric_val": range(12),
                "sample_name": runs,
            }
        )

        fig = create_raincloud_figure(
            df=df,
            tool_name="Test Tool",
            metric_name="metric_val",
            num_runs=None,
            color_col=None,
            violin_side="positive",
            plot_components=["violin"],
        )

        assert all(t.line.color for t in fig.data)
        assert not fig.layout.showlegend
        assert "all runs" in fig.layout.title.text
