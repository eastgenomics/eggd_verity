import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import Input, Output, callback, dcc, html, no_update
from sqlmodel import select

from app.components import (
    create_plot_page_layout,
    create_sample_filter_control,
    create_warning_figure,
)
from app.db import get_session
from app.plot_utils import format_categorical_columns, register_hover_callbacks
from app.utils import get_metric_models, get_numeric_fields, get_plot_grouping_options
from data.models.reports import Assay, Run, Sample

dash.register_page(__name__, path="/trends", name="Metric Trends")

TOOL_MODEL_MAP = get_metric_models()


# Layout

controls = dbc.Card(
    [
        dbc.Label("1. Select Assay(s)"),
        dcc.Dropdown(
            id="assay-dropdown",
            placeholder="Select one or more assays...",
            multi=True,
        ),
        dbc.Label("2. Select QC Tool", className="mt-2"),
        dcc.Dropdown(id="tool-dropdown", placeholder="Select a tool..."),
        dbc.Label("3. Select Metric", className="mt-2"),
        dcc.Dropdown(
            id="metric-dropdown", placeholder="Select metric(s)...", multi=True
        ),
        dbc.Label("4. Number of Recent Runs", className="mt-2"),
        html.Br(),
        dcc.Input(
            id="trends-num-runs-input",
            type="number",
            min=1,
            value=10,
            
        ),
        html.Hr(),
        dbc.Label("5. Customise Plot", className="fw-bold mt-2"),
        html.Br(),
        dbc.Label("Plot Type", className="mt-2"),
        dbc.RadioItems(
            id="plot-type-radio",
            options=[
                {"label": "Scatter", "value": "scatter"},
                {"label": "Line", "value": "line"},
            ],
            value="scatter",
            inline=True,
        ),
        dbc.Label("Colour By", className="mt-2"),
        dcc.Dropdown(id="color-by-dropdown", placeholder="Select a category..."),
        dbc.Label("Symbol By", className="mt-2"),
        dcc.Dropdown(id="symbol-by-dropdown", placeholder="Select a category..."),
        dbc.Label("Marker Size", className="mt-2"),
        dcc.Slider(id="trends-marker-size-slider", min=2, max=20, step=1, value=6),
        html.Hr(),
        dbc.Label("6. Plot Options", className="fw-bold mt-2"),
        html.Br(),
        dbc.Label("Y-Axis Transform", className="mt-2"),
        dbc.RadioItems(
            id="yaxis-transform-radio",
            options=[
                {"label": "Linear (Raw)", "value": "linear"},
                {"label": "Log", "value": "log"},
                {"label": "Standardise (Z-score)", "value": "standardise"},
            ],
            value="linear",
            inline=True,
        ),
        dbc.Checklist(
            options=[{"label": "Show Mean & Std Dev", "value": "show_stats"}],
            value=[],
            id="stats-lines-checklist",
            className="mt-2",
        ),
    ],
    body=True,
    className="mb-4",
)

layout = html.Div(
    [
        create_sample_filter_control(),
        create_plot_page_layout(
            controls, "trends-plot", "trends-hover-data-box", "Metric Trends Over Time"
        ),
    ]
)

# Callbacks

register_hover_callbacks("trends")


@callback(Output("assay-dropdown", "options"), Input("assay-dropdown", "id"))
def populate_assays(_):
    """Populates the assay dropdown with all available assay names."""
    with get_session() as session:
        assays = session.exec(select(Assay.name).distinct()).all()
        return sorted(assays)


@callback(Output("tool-dropdown", "options"), Input("tool-dropdown", "id"))
def populate_tools(_):
    """Populates the tool dropdown with all discovered metric models."""
    return list(TOOL_MODEL_MAP.keys())


@callback(Output("metric-dropdown", "options"), Input("tool-dropdown", "value"))
def populate_metrics(tool_name):
    """Populates the metric dropdown based on the selected tool."""
    if not tool_name:
        return []
    model = TOOL_MODEL_MAP[tool_name]
    fields = get_numeric_fields(model)
    # Convert snake_case to Title Case for display
    return [
        {"label": field.replace("_", " ").title(), "value": field} for field in fields
    ]


@callback(Output("metric-dropdown", "value"), Input("tool-dropdown", "value"))
def reset_metric_on_tool_change(_):
    """Resets the metric dropdown when the tool changes to prevent errors."""
    return None


@callback(
    Output("yaxis-transform-radio", "value"),
    Output("yaxis-transform-radio", "disabled"),
    Output("stats-lines-checklist", "value"),
    Output("stats-lines-checklist", "disabled"),
    Output("color-by-dropdown", "disabled"),
    Input("metric-dropdown", "value"),
)
def manage_plot_options(selected_metrics):
    """Disables plot options that are not applicable to multi-metric view."""
    is_multi_metric = selected_metrics and len(selected_metrics) > 1
    if is_multi_metric:
        # Force Z-score, disable radio, disable/uncheck stats, disable colour dropdown
        return "standardise", True, [], True, True
    else:
        # Re-enable all options for single-metric view
        return dash.no_update, False, dash.no_update, False, False


@callback(
    Output("color-by-dropdown", "options"),
    Output("symbol-by-dropdown", "options"),
    Input("color-by-dropdown", "id"),
)
def populate_grouping_options(_):
    """Populates the 'Color By' and 'Symbol By' dropdowns."""
    options = get_plot_grouping_options()

    formatted_options = []

    for group_name, opts in options.items():
        for opt in opts:
            formatted_options.append(
                {
                    "label": f"{group_name}: {opt.replace('_', ' ').title()}",
                    "value": f"{group_name.lower()}.{opt}",
                }
            )
    return formatted_options, formatted_options


@callback(
    Output("trends-plot", "figure"),
    [
        Input("assay-dropdown", "value"),
        Input("tool-dropdown", "value"),
        Input("metric-dropdown", "value"),
        Input("plot-type-radio", "value"),
        Input("color-by-dropdown", "value"),
        Input("symbol-by-dropdown", "value"),
        Input("yaxis-transform-radio", "value"),
        Input("stats-lines-checklist", "value"),
        Input("trends-marker-size-slider", "value"),
        Input("trends-num-runs-input", "value"),
        Input("sample-filter-store", "data"),
    ],
)
def update_trends_plot(
    assay_names,
    tool_name,
    metric_names,
    plot_type,
    color_by,
    symbol_by,
    yaxis_transform,
    stats_lines,
    marker_size,
    num_runs,
    sample_filter,
):
    """Updates the main plot based on user selections."""
    if not all([assay_names, tool_name, metric_names]):
        return create_warning_figure(
            "Please select at least one assay, a tool, and a metric to plot."
        )

    is_multi_metric = len(metric_names) > 1
    tool_model = TOOL_MODEL_MAP[tool_name]

    is_run_level = tool_model.metric_level == "run"

    columns_to_select = [
        Run.date,
        Run.run_folder,
    ]
    # Only add sample name for sample-level metrics
    if not is_run_level:
        columns_to_select.append(Sample.name.label("sample_name"))

    df_cols = ["date", "run_folder"]
    if not is_run_level:
        df_cols.append("sample_name")

    for metric in metric_names:
        columns_to_select.append(getattr(tool_model, metric).label(metric))
        df_cols.append(metric)

    # Process unique grouping factors to avoid duplicate columns in the query
    grouping_args = {"color": None, "symbol": None}
    unique_group_vals = {val for val in [color_by, symbol_by] if val}
    for arg_val in unique_group_vals:
        model_name, field_name = arg_val.split(".")
        if model_name == "run":
            model = Run
        elif model_name == "sample":
            model = Sample
        elif model_name == "assay":
            model = Assay
        else:
            continue  # Should not happen

        unique_alias = f"{model_name}_{field_name}"
        columns_to_select.append(getattr(model, field_name).label(unique_alias))
        df_cols.append(unique_alias)

    # Map the selected values back to the plotly arguments
    if color_by:
        grouping_args["color"] = f"{color_by.split('.')[0]}_{color_by.split('.')[1]}"
    if symbol_by:
        grouping_args["symbol"] = f"{symbol_by.split('.')[0]}_{symbol_by.split('.')[1]}"

    with get_session() as session:
        if is_run_level:
            statement = (
                select(*columns_to_select)
                .join(tool_model, Run.id == tool_model.run_id)
                .join(Assay, Run.assay_id == Assay.id)
                .where(Assay.name.in_(assay_names))
            )
            if num_runs:
                statement = statement.order_by(Run.date.desc()).limit(num_runs)

        else:
            statement = (
                select(*columns_to_select)
                .join(Sample, Run.id == Sample.run_id)
                .join(tool_model, Sample.id == tool_model.sample_id)
                .join(Assay, Run.assay_id == Assay.id)
                .where(Assay.name.in_(assay_names))
                .where(
                    getattr(tool_model, metric_names[0]).is_not(None)
                )
            )
            if sample_filter == "controls_only":
                statement = statement.where(Sample.is_control == True)
            if num_runs:
                # To get the latest N runs with sample data, we need a subquery
                run_ids_subquery = (
                    statement.with_only_columns(Run.id)
                    .distinct()
                    .order_by(Run.date.desc())
                    .limit(num_runs)
                )
                statement = statement.where(Run.id.in_(run_ids_subquery))

        results = session.exec(statement).all()

    if not results:
        return create_warning_figure(
            f"No data found for the selected metrics in the selected assays."
        )

    df = pd.DataFrame(results, columns=df_cols)
    # Convert to date objects to remove the time component from the axis
    df = df.sort_values("date", ascending=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    df = format_categorical_columns(df, color_by, symbol_by, grouping_args)

    # Data Reshaping and Plotting
    # Choose plot type
    plot_func = px.scatter if plot_type == "scatter" else px.line

    if is_multi_metric:
        # For run-level metrics, hover name should be the run folder
        hover_name = "sample_name" if not is_run_level else "run_folder"
        id_vars = ["date", "run_folder"]
        if not is_run_level:
            id_vars.append("sample_name")
        if grouping_args["symbol"]:
            id_vars.append(grouping_args["symbol"])

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
            symbol=grouping_args["symbol"],
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
        # For run-level metrics, hover name should be the run folder
        hover_name = "sample_name" if not is_run_level else "run_folder"
        df.rename(columns={metric_name: "metric_value"}, inplace=True)
        metric_label = metric_name.replace("_", " ").title()

        if yaxis_transform == "standardise":
            mean_value, std_value = df["metric_value"].mean(), df["metric_value"].std()
            if std_value > 0:
                df["metric_value"] = (df["metric_value"] - mean_value) / std_value
            else:
                df["metric_value"] = 0
            metric_label = f"{metric_label} (Z-score)"

        plot_title = f"Trend for {tool_name}: {metric_label}"

        fig = plot_func(
            df,
            x="date",
            y="metric_value",
            color=grouping_args["color"],
            symbol=grouping_args["symbol"],
            hover_name=hover_name,
            custom_data=["run_folder"],
            title=plot_title,
            labels={"metric_value": metric_label, "date": "Run Date"},
        )

        fig.update_traces(
            hovertemplate=(
                f"<b>%{{hovertext}}</b><br><br>"
                f"Run Folder: %{{customdata[0]}}<br>"
                f"Date: %{{x}}<br>"
                f"{metric_label}: %{{y:.3f}}"
                f"<extra></extra>"
            )
        )

        if "show_stats" in stats_lines and yaxis_transform == "linear":
            mean_value = df["metric_value"].mean()
            std_value = df["metric_value"].std()
            upper_bound = mean_value + 3 * std_value
            lower_bound = mean_value - 3 * std_value

            fig.add_hline(
                y=mean_value,
                line_dash="solid",
                line_color="green",
                annotation_text="Mean",
            )
            fig.add_hline(
                y=upper_bound,
                line_dash="dash",
                line_color="red",
                annotation_text="+3 Std Dev",
            )
            fig.add_hline(
                y=lower_bound,
                line_dash="dash",
                line_color="red",
                annotation_text="-3 Std Dev",
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
