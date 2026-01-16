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
from app.utils import register_hover_callbacks
from data.models.reports import Assay, Run
from data.plots.correlation import create_correlation_figure
from data.queries.correlation import get_correlation_data
from data.queries.general import get_assay_names, get_available_tools
from data.utils.model_utils import get_metric_models, get_plot_grouping_options

dash.register_page(__name__, path="/correlation", name="Correlation")

TOOL_MODEL_MAP = get_metric_models()


def make_metric_selector_components(axis_prefix):
    """Helper to create tool and metric selector components for an axis (X or Y)."""
    return [
        dbc.Label(f"{axis_prefix.upper()}-Axis Tool", className="mt-2"),
        dcc.Dropdown(id=f"{axis_prefix}-tool-dropdown", placeholder="Select a tool..."),
        dbc.Label(f"{axis_prefix.upper()}-Axis Metric", className="mt-2"),
        dcc.Dropdown(
            id=f"{axis_prefix}-metric-dropdown", placeholder="Select a metric..."
        ),
    ]


controls = dbc.Card(
    [
        dbc.Label("1. Select Filters", className="fw-bold"),
        html.Br(),
        dbc.Label("Assay(s)"),
        dcc.Dropdown(
            id="corr-assay-dropdown", placeholder="Select assays...", multi=True
        ),
        dbc.Label("Run(s) (optional)", className="mt-2"),
        dcc.Dropdown(
            id="corr-run-dropdown",
            placeholder="Search by run folder...",
            multi=True,
        ),
        html.Div(id="run-limit-warning", className="text-danger small mt-1"),
        html.Hr(),
        dbc.Label("2. Select Metrics", className="fw-bold"),
        html.Br(),
        *make_metric_selector_components("x"),
        *make_metric_selector_components("y"),
        html.Hr(),
        dbc.Label("3. Customise Plot", className="fw-bold mt-2"),
        html.Br(),
        dbc.Label("Colour By", className="mt-2"),
        dcc.Dropdown(id="corr-color-by-dropdown", placeholder="Select a category..."),
        dbc.Label("Symbol By", className="mt-2"),
        dcc.Dropdown(id="corr-symbol-by-dropdown", placeholder="Select a category..."),
        dbc.Label("Marker Size", className="mt-2"),
        dcc.Slider(id="corr-marker-size-slider", min=2, max=20, step=1, value=6),
        html.Hr(),
        dbc.Label("4. Analysis", className="fw-bold mt-2"),
        html.Br(),
        dbc.Label("Trendline", className="mt-2"),
        dcc.Dropdown(
            id="corr-trendline-dropdown",
            options=[
                {"label": "None", "value": "none"},
                {"label": "Linear (OLS)", "value": "ols"},
                {"label": "Locally Weighted (LOWESS)", "value": "lowess"},
            ],
            value="none",
        ),
        html.Hr(),
        dbc.Label("5. Axis Options", className="fw-bold mt-2"),
        html.Br(),
        dbc.Label("X-Axis Transform", className="mt-2"),
        dbc.RadioItems(
            id="corr-xaxis-transform-radio",
            options=[
                {"label": "Linear", "value": "linear"},
                {"label": "Log", "value": "log"},
                {"label": "Standardise (Z-score)", "value": "standardise"},
            ],
            value="linear",
            inline=True,
        ),
        dbc.Label("Y-Axis Transform", className="mt-2"),
        dbc.RadioItems(
            id="corr-yaxis-transform-radio",
            options=[
                {"label": "Linear", "value": "linear"},
                {"label": "Log", "value": "log"},
                {"label": "Standardise (Z-score)", "value": "standardise"},
            ],
            value="linear",
            inline=True,
        ),
    ],
    body=True,
)

layout = html.Div(
    [
        create_sample_filter_control(),
        create_plot_page_layout(
            controls,
            "correlation-plot",
            "correlation-hover-data-box",
            "Correlate QC Metrics",
        ),
    ]
)

######## Callbacks

register_hover_callbacks("correlation")


# Populate shared dropdowns
@callback(Output("corr-assay-dropdown", "options"), Input("corr-assay-dropdown", "id"))
def populate_assays(_):
    with get_session() as session:
        return get_assay_names(session)


@callback(
    Output("corr-color-by-dropdown", "options"),
    Output("corr-symbol-by-dropdown", "options"),
    Input("corr-color-by-dropdown", "id"),
)
def populate_grouping_options(_):
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
    Output("corr-run-dropdown", "options"),
    Output("corr-run-dropdown", "value"),
    Input("corr-assay-dropdown", "value"),
)
def update_run_dropdown(assay_names):
    """Populates the run dropdown based on selected assays and resets its value."""
    if not assay_names:
        return [], None

    with get_session() as session:
        stmt = (
            select(Run.run_folder)
            .join(Assay)
            .where(Assay.name.in_(assay_names))
            .distinct()
            .order_by(Run.date.desc())
        )
        runs = session.exec(stmt).all()
        # The dropdown can take a list of strings directly for options
        return runs, None


MAX_RUNS_SELECTION = 5


@callback(
    Output("corr-run-dropdown", "value", allow_duplicate=True),
    Output("run-limit-warning", "children"),
    Output("run-limit-warning", "hidden"),
    Input("corr-run-dropdown", "value"),
    prevent_initial_call=True,
)
def limit_run_selection(selected_runs):
    """Limits the number of runs that can be selected."""
    if not selected_runs:
        return [], "", True

    if len(selected_runs) > MAX_RUNS_SELECTION:
        limited_runs = selected_runs[:MAX_RUNS_SELECTION]
        warning_msg = f"You can only select a maximum of {MAX_RUNS_SELECTION} runs."
        return limited_runs, warning_msg, False

    # If selection is valid, hide the warning
    return dash.no_update, "", True


@callback(
    Output("x-tool-dropdown", "options"),
    Output("y-tool-dropdown", "options"),
    Input("corr-assay-dropdown", "value"),
)
def populate_correlation_tools(assay_names):
    """Populates both X and Y tool dropdowns based on selected assays."""
    if not assay_names:
        return [], []

    sample_level_map = {
        name: model
        for name, model in TOOL_MODEL_MAP.items()
        if model.metric_level == "sample"
    }

    with get_session() as session:
        tools = get_available_tools(session, assay_names, sample_level_map)
        return tools, tools


# Populate and reset metric selectors for both X and Y axes
for axis in ["x", "y"]:

    @callback(
        Output(f"{axis}-metric-dropdown", "options"),
        Input(f"{axis}-tool-dropdown", "value"),
    )
    def populate_metrics(tool_name):
        if not tool_name:
            return []
        model = TOOL_MODEL_MAP[tool_name]
        fields = model.numeric_fields
        return [
            {"label": field.replace("_", " ").title(), "value": field}
            for field in fields
        ]

    @callback(
        Output(f"{axis}-metric-dropdown", "value"),
        Input(f"{axis}-tool-dropdown", "value"),
    )
    def reset_metric(_):
        return None


# Main plotting callback
@callback(
    Output("correlation-plot", "figure"),
    [
        Input("corr-assay-dropdown", "value"),
        Input("corr-run-dropdown", "value"),
        Input("x-tool-dropdown", "value"),
        Input("x-metric-dropdown", "value"),
        Input("y-tool-dropdown", "value"),
        Input("y-metric-dropdown", "value"),
        Input("corr-color-by-dropdown", "value"),
        Input("corr-symbol-by-dropdown", "value"),
        Input("corr-marker-size-slider", "value"),
        Input("corr-trendline-dropdown", "value"),
        Input("corr-xaxis-transform-radio", "value"),
        Input("corr-yaxis-transform-radio", "value"),
        Input("sample-filter-store", "data"),
    ],
)
def update_correlation_plot(
    assay_names,
    run_folders,
    x_tool,
    x_metric,
    y_tool,
    y_metric,
    color_by,
    symbol_by,
    marker_size,
    trendline,
    xaxis_transform,
    yaxis_transform,
    sample_filter,
):
    if not all([assay_names, x_tool, x_metric, y_tool, y_metric]):
        return create_warning_figure(
            "Please select assays and metrics for both X and Y axes."
        )

    x_model = TOOL_MODEL_MAP[x_tool]
    y_model = TOOL_MODEL_MAP[y_tool]

    with get_session() as session:
        df, grouping_args = get_correlation_data(
            session,
            assay_names,
            run_folders,
            x_model,
            x_metric,
            y_model,
            y_metric,
            sample_filter,
            color_by,
            symbol_by,
        )

    if df.empty:
        return create_warning_figure(
            "No data found for the selected combination of metrics."
        )

    return create_correlation_figure(
        df,
        x_metric,
        y_metric,
        grouping_args["color"],
        grouping_args["symbol"],
        marker_size,
        trendline,
        xaxis_transform,
        yaxis_transform,
    )
