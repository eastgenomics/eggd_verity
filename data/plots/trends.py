import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data.utils.formatting import run_label, run_sample_counts

# Project names are long, so x tick labels drop the number prefix and are cut to
# this many characters. The full name is still shown in the hover.
MAX_RUN_LABEL_LENGTH = 20
FIGURE_HEIGHT = 580


def truncate_label(label: str, max_length: int = MAX_RUN_LABEL_LENGTH) -> str:
    """Shortens a label to max_length characters, ending in an ellipsis."""
    label = str(label)
    return label if len(label) <= max_length else f"{label[: max_length - 1]}…"


def create_trends_figure(
    df: pd.DataFrame,
    tool_name: str,
    metric_names: list[str],
    plot_type: str,
    color_col: str | None,
    symbol_col: str | None,
    yaxis_transform: str,
    show_stats: list[str],
    marker_size: int,
    is_run_level: bool,
) -> go.Figure:
    """
    Generates the trends plot figure, with one x axis category per run.
    """
    df = df.copy()
    is_multi_metric = len(metric_names) > 1
    is_box = plot_type == "box"
    hover_name = "sample_name" if not is_run_level else "project_name"
    samples_line = "" if is_run_level else "Samples in run: %{customdata[2]}<br>"

    # Runs arrive sorted by date. Fix the category order explicitly, otherwise
    # Plotly orders runs by first appearance across traces when grouping is on.
    ordered_runs = list(df["project_name"].unique())

    def add_run_samples(data, value_col, by=()):
        # Run-level tools have one row per run, so there is no sample count
        if is_run_level:
            data["run_samples"] = None
        else:
            data["run_samples"] = run_sample_counts(data, value_col, by)
        return data

    def plot(data, **kwargs):
        if is_box:
            # px.box has no symbol argument
            kwargs.pop("symbol", None)
            return px.box(data, notched=True, points="all", **kwargs)
        return px.scatter(data, **kwargs)

    if is_multi_metric:
        id_vars = ["date", "project_name"]
        if not is_run_level:
            id_vars.append("sample_name")
        if symbol_col:
            id_vars.append(symbol_col)

        df_long = df.melt(
            id_vars=id_vars,
            value_vars=metric_names,
            var_name="Metric",
            value_name="Value",
        )

        df_long = add_run_samples(df_long, "Value", by=["Metric"])

        # Standardise each metric's values independently
        df_long["Value"] = df_long.groupby("Metric")["Value"].transform(
            lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
        )

        fig = plot(
            df_long,
            x="project_name",
            y="Value",
            color="Metric",
            symbol=symbol_col,
            hover_name=hover_name,
            custom_data=["project_name", "date", "run_samples", "Metric"],
            category_orders={"project_name": ordered_runs},
            title=f"Trends for {tool_name}",
            labels={"Value": "Value (Z-score)", "project_name": "Run"},
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br><br>"
                "Run: %{customdata[0]}<br>"
                "Date: %{customdata[1]}<br>"
                f"{samples_line}"
                "Metric: %{customdata[3]}<br>"
                "Value (Z-score): %{y:.3f}<extra></extra>"
            )
        )
    else:
        metric_name = metric_names[0]
        df = df.rename(columns={metric_name: "metric_value"})
        metric_label = metric_name.replace("_", " ").title()
        df = add_run_samples(df, "metric_value")

        if yaxis_transform == "standardise":
            mean_val, std_val = df["metric_value"].mean(), df["metric_value"].std()
            df["metric_value"] = (
                (df["metric_value"] - mean_val) / std_val if std_val > 0 else 0
            )
            metric_label = f"{metric_label} (Z-score)"

        fig = plot(
            df,
            x="project_name",
            y="metric_value",
            color=color_col,
            symbol=symbol_col,
            hover_name=hover_name,
            custom_data=["project_name", "date", "run_samples"],
            category_orders={"project_name": ordered_runs},
            title=f"Trend for {tool_name}: {metric_label}",
            labels={"metric_value": metric_label, "project_name": "Run"},
        )
        fig.update_traces(
            hovertemplate=(
                f"<b>%{{hovertext}}</b><br><br>"
                f"Run: %{{customdata[0]}}<br>"
                f"Date: %{{customdata[1]}}<br>"
                f"{samples_line}"
                f"{metric_label}: %{{y:.3f}}<extra></extra>"
            )
        )

        if "show_stats" in show_stats and yaxis_transform == "linear":
            mean_val = df["metric_value"].mean()
            std_val = df["metric_value"].std()
            fig.add_hline(
                y=mean_val,
                line_dash="solid",
                line_width=1,
                line_color="green",
                annotation_text="Mean",
            )
            fig.add_hline(
                y=mean_val + 3 * std_val,
                line_dash="dash",
                line_width=1,
                line_color="red",
                annotation_text="+3 SD",
            )
            fig.add_hline(
                y=mean_val - 3 * std_val,
                line_dash="dash",
                line_width=1,
                line_color="red",
                annotation_text="-3 SD",
            )

        if yaxis_transform == "log":
            fig.update_yaxes(type="log")

    if is_box:
        # Hover on the sample points only; the custom template has no box stats
        fig.update_traces(hoveron="points")
    fig.update_traces(marker=dict(size=marker_size, opacity=0.7))
    fig.update_xaxes(
        tickangle=-45,
        tickmode="array",
        tickvals=ordered_runs,
        ticktext=[truncate_label(run_label(run)) for run in ordered_runs],
        tickfont=dict(size=10),
    )
    fig.update_layout(
        height=FIGURE_HEIGHT,
        margin=dict(l=20, r=20, t=50, b=20),
        legend_title_text="Group By",
        title_font=dict(size=18, weight="bold"),
    )
    return fig
