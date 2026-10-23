from itertools import cycle

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data.utils.formatting import run_label, run_sample_counts


MAX_ASSAYS_IN_TITLE = 3


def format_assay_names(assay_names: list[str] | None) -> str:
    """
    Joins assay names for the plot title, e.g. "A, B, C +2 more", so that a long
    selection does not push the title off the plot.
    """
    if not assay_names:
        return ""
    shown = ", ".join(assay_names[:MAX_ASSAYS_IN_TITLE])
    hidden = len(assay_names) - MAX_ASSAYS_IN_TITLE
    return f"{shown} +{hidden} more" if hidden > 0 else shown


def create_raincloud_figure(
    df: pd.DataFrame,
    tool_name: str,
    metric_name: str,
    num_runs: int | None,
    color_col: str | None,
    violin_side: str,
    plot_components: list[str],
    color_label: str | None = None,
    assay_names: list[str] | None = None,
) -> go.Figure:
    """
    Generates the raincloud plot figure.

    With no colour column each run gets its own colour. A colour column that is
    constant within each run (e.g. sequencer) colours the whole run. One that
    varies within a run (e.g. a sample field) colours each sample point, and the
    violins and boxes are drawn in a neutral colour.
    """
    df = df.copy()
    if "assay_name" not in df.columns:
        df["assay_name"] = ""
    ordered_runs = df["project_name"].unique()
    # Samples with a value in each run, shown in the hover box
    df["run_samples"] = run_sample_counts(df, metric_name)

    if color_col:
        df[color_col] = df[color_col].fillna("N/A").astype(str)
        group_col = color_col
    else:
        group_col = "project_name"

    categories = df[group_col].unique()
    color_discrete_map = dict(zip(categories, cycle(px.colors.qualitative.Plotly)))
    per_sample = bool(color_col) and (
        df.groupby("project_name")[color_col].nunique().max() > 1
    )
    show_legend = bool(color_col)
    neutral_color = "#7f7f7f"

    def run_style(df_run):
        """Colour and legend group for a trace covering a whole run."""
        if per_sample:
            return dict(marker_color=neutral_color, legendgroup=None)
        category = df_run[group_col].iloc[0]
        return dict(
            marker_color=color_discrete_map[category],
            legendgroup=category if show_legend else None,
        )

    fig = go.Figure()

    if "violin" in plot_components:
        for run in ordered_runs:
            df_run = df[df["project_name"] == run]
            style = run_style(df_run)
            fig.add_trace(
                go.Violin(
                    x=df_run["project_name"],
                    y=df_run[metric_name],
                    name=str(df_run[group_col].iloc[0]) if show_legend else run,
                    side=violin_side if violin_side != "both" else None,
                    width=0.8,
                    line_color=style["marker_color"],
                    legendgroup=style["legendgroup"],
                    showlegend=False,
                )
            )

    if "box" in plot_components:
        for run in ordered_runs:
            df_run = df[df["project_name"] == run]
            style = run_style(df_run)
            fig.add_trace(
                go.Box(
                    x=df_run["project_name"],
                    y=df_run[metric_name],
                    name=str(df_run[group_col].iloc[0]) if show_legend else run,
                    marker_color=style["marker_color"],
                    legendgroup=style["legendgroup"],
                    showlegend=False,
                    boxpoints=False,
                    width=0.15,
                    offsetgroup=f"{run}_box",
                    boxmean=True,
                )
            )

    if "points" in plot_components:
        pointpos_map = {"positive": -0.6, "negative": 0.6, "both": 0}
        pointpos = pointpos_map.get(violin_side, 0)
        for run in ordered_runs:
            df_run = df[df["project_name"] == run]
            # One trace per colour within the run, so each sample keeps its colour
            for category, df_cat in df_run.groupby(group_col, sort=False):
                fig.add_trace(
                    go.Box(
                        x=df_cat["project_name"],
                        y=df_cat[metric_name],
                        name=str(category) if show_legend else run,
                        legendgroup=category if show_legend else None,
                        showlegend=False,
                        boxpoints="all",
                        jitter=0.2,
                        pointpos=pointpos,
                        marker_color=color_discrete_map[category],
                        marker=dict(size=5 if per_sample else 3, opacity=0.7),
                        line_width=0,
                        fillcolor="rgba(0,0,0,0)",
                        hoveron="points",
                        hovertext=df_cat["sample_name"],
                        customdata=df_cat[["project_name", "assay_name", "run_samples"]],
                        hovertemplate=(
                            "<b>%{hovertext}</b><br>"
                            "Run: %{customdata[0]}<br>"
                            "Assay: %{customdata[1]}<br>"
                            "Samples in run: %{customdata[2]}<br>"
                            "%{y:.3f}<extra>%{fullData.name}</extra>"
                        ),
                        width=0.7,
                    )
                )

    # One marker per category in the legend. Clicking it toggles every trace in
    # that category's legend group.
    if show_legend:
        for category in categories:
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="markers",
                    name=str(category),
                    legendgroup=category,
                    marker=dict(color=color_discrete_map[category], size=10),
                )
            )

    metric_title = metric_name.replace("_", " ").title()
    runs_text = f"the last {num_runs} run(s)" if num_runs else "all runs"
    title = f"{tool_name}: {metric_title} for {runs_text}"
    if assay_text := format_assay_names(assay_names):
        title = f"{title} ({assay_text})"
    fig.update_layout(
        title=title,
        title_font=dict(size=20, family="Arial", color="black"),
        violingap=0,
        violinmode="overlay",
        boxmode="overlay",
        xaxis_tickangle=-45,
        xaxis=dict(
            categoryorder="array",
            categoryarray=ordered_runs,
            tickmode="array",
            tickvals=ordered_runs,
            ticktext=[run_label(run) for run in ordered_runs],
            tickfont=dict(size=10),
        ),
        margin=dict(t=50, l=60, r=20, b=20),
        showlegend=show_legend,
        legend_title_text=color_label or "",
        yaxis_title=metric_title,
        xaxis_title="Run",
    )
    return fig
