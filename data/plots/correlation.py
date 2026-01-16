import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def create_correlation_figure(
    df: pd.DataFrame,
    x_metric: str,
    y_metric: str,
    color_col: str | None,
    symbol_col: str | None,
    marker_size: int,
    trendline: str,
    xaxis_transform: str,
    yaxis_transform: str,
) -> go.Figure:
    """
    Generates the correlation plot figure.
    """
    x_label = x_metric.replace("_", " ").title()
    y_label = y_metric.replace("_", " ").title()

    # Transformations
    if xaxis_transform == "log":
        df = df[df["x"] > 0]
    if yaxis_transform == "log":
        df = df[df["y"] > 0]

    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Correlation: {x_label} vs. {y_label}",
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[
                {
                    "text": "No data points remain after applying filters (e.g. Log scale on non-positive values).",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 14},
                }
            ],
        )
        return fig

    if xaxis_transform == "standardise":
        mean_val, std_val = df["x"].mean(), df["x"].std()
        df["x"] = (df["x"] - mean_val) / std_val if std_val > 0 else 0
        x_label = f"{x_label} (Z-score)"

    if yaxis_transform == "standardise":
        mean_val, std_val = df["y"].mean(), df["y"].std()
        df["y"] = (df["y"] - mean_val) / std_val if std_val > 0 else 0
        y_label = f"{y_label} (Z-score)"

    trendline_arg = trendline if trendline != "none" else None

    fig = px.scatter(
        df,
        x="x",
        y="y",
        color=color_col,
        symbol=symbol_col,
        hover_name="sample_name",
        custom_data=["run_folder"],
        labels={"x": x_label, "y": y_label},
        title=f"Correlation: {x_label} vs. {y_label}",
        trendline=trendline_arg,
    )

    fig.update_traces(
        hovertemplate=(
            f"<b>%{{hovertext}}</b><br><br>"
            f"Run Folder: %{{customdata[0]}}<br>"
            f"{x_label}: %{{x:.3f}}<br>"
            f"{y_label}: %{{y:.3f}}<extra></extra>"
        )
    )

    if trendline == "ols" and not color_col:
        try:
            results = px.get_trendline_results(fig)
            r_squared = results.iloc[0]["px_fit_results"].rsquared
            fig.update_layout(title=f"{fig.layout.title.text} (R² = {r_squared:.3f})")
        except (IndexError, AttributeError):
            pass

    if xaxis_transform == "log":
        fig.update_xaxes(type="log")
    if yaxis_transform == "log":
        fig.update_yaxes(type="log")
    fig.update_traces(marker=dict(size=marker_size))
    fig.update_layout(
        height=700,
        margin=dict(l=20, r=20, t=50, b=20),
        legend_title_text="Group By",
        title_font=dict(size=18, weight="bold"),
    )
    return fig
