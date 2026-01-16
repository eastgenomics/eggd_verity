import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def create_raincloud_figure(
    df: pd.DataFrame,
    tool_name: str,
    metric_name: str,
    num_runs: int,
    color_col: str | None,
    violin_side: str,
    plot_components: list[str],
) -> go.Figure:
    """
    Generates the raincloud plot figure.
    """
    ordered_runs = df["run_folder"].unique()

    # Colour mapping
    color_discrete_map = None
    if not color_col or color_col == "run_run_folder":
        color_col = "run_folder"
        unique_runs = df["run_folder"].unique()
        color_discrete_map = {
            run: color for run, color in zip(unique_runs, px.colors.qualitative.Plotly)
        }
    else:
        unique_colors = df[color_col].unique()
        color_discrete_map = {
            cat: color
            for cat, color in zip(unique_colors, px.colors.qualitative.Plotly)
        }
        df["color"] = df[color_col].map(color_discrete_map)

    fig = go.Figure()

    if "violin" in plot_components:
        for run in ordered_runs:
            df_run = df[df["run_folder"] == run]
            fig.add_trace(
                go.Violin(
                    x=df_run["run_folder"],
                    y=df_run[metric_name],
                    name=run,
                    side=violin_side if violin_side != "both" else None,
                    width=0.8,
                    line_color=(
                        color_discrete_map.get(df_run[color_col].iloc[0])
                        if color_col != "run_folder"
                        else color_discrete_map.get(run)
                    ),
                    showlegend=False,
                )
            )

    if "box" in plot_components:
        offset_map = {"positive": 0.15, "negative": -0.15, "both": 0}
        offset = offset_map.get(violin_side, 0)
        for run in ordered_runs:
            df_run = df[df["run_folder"] == run]
            fig.add_trace(
                go.Box(
                    x=df_run["run_folder"],
                    y=df_run[metric_name],
                    name=run,
                    marker_color=(
                        color_discrete_map.get(df_run[color_col].iloc[0])
                        if color_col != "run_folder"
                        else color_discrete_map.get(run)
                    ),
                    boxpoints=False,
                    width=0.15,
                    offsetgroup=f"{run}_box",
                    x0=offset,
                    showlegend=False,
                    boxmean=True,
                )
            )

    if "points" in plot_components:
        pointpos_map = {"positive": -0.6, "negative": 0.6, "both": 0}
        pointpos = pointpos_map.get(violin_side, 0)
        for run in ordered_runs:
            df_run = df[df["run_folder"] == run]
            fig.add_trace(
                go.Box(
                    x=df_run["run_folder"],
                    y=df_run[metric_name],
                    name=run,
                    boxpoints="all",
                    jitter=0.2,
                    pointpos=pointpos,
                    marker_color=(
                        color_discrete_map.get(df_run[color_col].iloc[0])
                        if color_col != "run_folder"
                        else color_discrete_map.get(run)
                    ),
                    marker=dict(size=3, opacity=0.6),
                    line_width=0,
                    fillcolor="rgba(0,0,0,0)",
                    hoverinfo="y+name",
                    showlegend=False,
                    width=0.7,
                )
            )

    metric_title = metric_name.replace("_", " ").title()
    fig.update_layout(
        title=f"{tool_name}: {metric_title} for the last {num_runs} run(s)",
        title_font=dict(size=20, family="Arial", color="black"),
        violingap=0,
        violinmode="overlay",
        xaxis_tickangle=-45,
        xaxis=dict(categoryorder="array", categoryarray=ordered_runs),
        showlegend=True if color_col else False,
        yaxis_title=metric_title,
        xaxis_title="Run",
    )
    return fig
