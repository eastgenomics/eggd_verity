import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


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
    Generates the trends plot figure.
    """
    plot_func = px.scatter if plot_type == "scatter" else px.line
    is_multi_metric = len(metric_names) > 1

    if is_multi_metric:
        hover_name = "sample_name" if not is_run_level else "run_folder"
        id_vars = ["date", "run_folder"]
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

        # Standardise each metric's values independently
        df_long["Value"] = df_long.groupby("Metric")["Value"].transform(
            lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
        )

        fig = plot_func(
            df_long,
            x="date",
            y="Value",
            color="Metric",
            symbol=symbol_col,
            hover_name=hover_name,
            custom_data=["run_folder", "Metric"],
            title=f"Trends for {tool_name}",
            labels={"Value": "Value (Z-score)", "date": "Run Date"},
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br><br>"
                "Run Folder: %{customdata[0]}<br>"
                "Metric: %{customdata[1]}<br>"
                "Date: %{x}<br>"
                "Value (Z-score): %{y:.3f}<extra></extra>"
            )
        )
    else:
        metric_name = metric_names[0]
        hover_name = "sample_name" if not is_run_level else "run_folder"
        df.rename(columns={metric_name: "metric_value"}, inplace=True)
        metric_label = metric_name.replace("_", " ").title()

        if yaxis_transform == "standardise":
            mean_val, std_val = df["metric_value"].mean(), df["metric_value"].std()
            df["metric_value"] = (
                (df["metric_value"] - mean_val) / std_val if std_val > 0 else 0
            )
            metric_label = f"{metric_label} (Z-score)"

        fig = plot_func(
            df,
            x="date",
            y="metric_value",
            color=color_col,
            symbol=symbol_col,
            hover_name=hover_name,
            custom_data=["run_folder"],
            title=f"Trend for {tool_name}: {metric_label}",
            labels={"metric_value": metric_label, "date": "Run Date"},
        )
        fig.update_traces(
            hovertemplate=(
                f"<b>%{{hovertext}}</b><br><br>"
                f"Run Folder: %{{customdata[0]}}<br>"
                f"Date: %{{x}}<br>"
                f"{metric_label}: %{{y:.3f}}<extra></extra>"
            )
        )

        if "show_stats" in show_stats and yaxis_transform == "linear":
            mean_val = df["metric_value"].mean()
            std_val = df["metric_value"].std()
            fig.add_hline(
                y=mean_val,
                line_dash="solid",
                line_color="green",
                annotation_text="Mean",
            )
            fig.add_hline(
                y=mean_val + 3 * std_val,
                line_dash="dash",
                line_color="red",
                annotation_text="+3 SD",
            )
            fig.add_hline(
                y=mean_val - 3 * std_val,
                line_dash="dash",
                line_color="red",
                annotation_text="-3 SD",
            )

        if yaxis_transform == "log":
            fig.update_yaxes(type="log")

    fig.update_traces(marker=dict(size=marker_size, opacity=0.7))
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        legend_title_text="Group By",
        title_font=dict(size=18, weight="bold"),
    )
    return fig
