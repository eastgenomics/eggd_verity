import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def create_summary_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    chart_type: str,
    labels: dict | None = None,
) -> go.Figure:
    """Generates a bar or pie chart for summary data."""
    if chart_type == "pie":
        fig = px.pie(df, values=y_col, names=x_col, title=title)
    else:
        fig = px.bar(df, x=x_col, y=y_col, text=y_col, title=title, labels=labels)
        fig.update_traces(textposition="outside")

    fig.update_layout(margin=dict(t=40, b=10, l=10, r=10), xaxis_title=None)
    return fig
