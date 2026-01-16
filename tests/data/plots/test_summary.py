import pandas as pd
import plotly.graph_objects as go

from data.plots.summary import create_summary_chart


class TestSummaryPlot:
    def test_create_summary_chart_bar(self):
        """Tests creating a bar chart."""
        df = pd.DataFrame({"category": ["A", "B"], "count": [10, 20]})

        fig = create_summary_chart(
            df=df, x_col="category", y_col="count", title="Test Bar", chart_type="bar"
        )

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Test Bar"
        assert fig.data[0].type == "bar"

    def test_create_summary_chart_pie(self):
        """Tests creating a pie chart."""
        df = pd.DataFrame({"category": ["A", "B"], "count": [10, 20]})

        fig = create_summary_chart(
            df=df, x_col="category", y_col="count", title="Test Pie", chart_type="pie"
        )

        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Test Pie"
        assert fig.data[0].type == "pie"
