import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import Input, Output, callback, dcc, html, no_update

from app.components import (
    create_plot_page_layout,
    create_sample_filter_control,
    create_warning_figure,
)
from app.db import get_session
from app.utils import register_hover_callbacks
from data.plots.trends import create_trends_figure
from data.queries.general import get_assay_names, get_available_tools
from data.queries.trends import get_trends_data
from data.utils.model_utils import get_metric_models, get_plot_grouping_options

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
        return get_assay_names(session)


@callback(Output("tool-dropdown", "options"), Input("assay-dropdown", "value"))
def populate_tools(assay_names):
    """Populates the tool dropdown based on selected assays."""
    if not assay_names:
        return []
    with get_session() as session:
        return get_available_tools(session, assay_names, TOOL_MODEL_MAP)


@callback(Output("metric-dropdown", "options"), Input("tool-dropdown", "value"))
def populate_metrics(tool_name):
    """Populates the metric dropdown based on the selected tool."""
    if not tool_name:
        return []
    model = TOOL_MODEL_MAP[tool_name]
    fields = model.numeric_fields
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

    with get_session() as session:
        df, grouping_args = get_trends_data(
            session,
            assay_names,
            tool_model,
            metric_names,
            num_runs,
            sample_filter,
            color_by,
            symbol_by,
        )

    if df.empty:
        return create_warning_figure(
            f"No data found for the selected metrics in the selected assays."
        )

    return create_trends_figure(
        df,
        tool_name,
        metric_names,
        plot_type,
        grouping_args["color"],
        grouping_args["symbol"],
        yaxis_transform,
        stats_lines,
        marker_size,
        is_run_level,
    )
