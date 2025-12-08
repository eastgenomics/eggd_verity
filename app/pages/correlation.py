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
        *make_metric_selector_components("x"),
        *make_metric_selector_components("y"),
        html.Hr(),
        dbc.Label("3. Customise Plot", className="fw-bold mt-2"),
        dbc.Label("Colour By", className="mt-2"),
        dcc.Dropdown(id="corr-color-by-dropdown", placeholder="Select a category..."),
        dbc.Label("Symbol By", className="mt-2"),
        dcc.Dropdown(id="corr-symbol-by-dropdown", placeholder="Select a category..."),
        dbc.Label("Marker Size", className="mt-2"),
        dcc.Slider(id="corr-marker-size-slider", min=2, max=20, step=1, value=6),
        html.Hr(),
        dbc.Label("4. Analysis", className="fw-bold mt-2"),
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
        assays = session.exec(select(Assay.name).distinct()).all()
        return sorted(assays)


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


# Populate and reset metric selectors for both X and Y axes
for axis in ["x", "y"]:

    @callback(
        Output(f"{axis}-tool-dropdown", "options"),
        Input(f"{axis}-tool-dropdown", "id"),
    )
    def populate_tools(_):
        # Filter out run-level metrics for the correlation plot
        sample_level_tools = [
            name
            for name, model in TOOL_MODEL_MAP.items()
            if model.metric_level == "sample"
        ]
        return sample_level_tools

    @callback(
        Output(f"{axis}-metric-dropdown", "options"),
        Input(f"{axis}-tool-dropdown", "value"),
    )
    def populate_metrics(tool_name):
        if not tool_name:
            return []
        model = TOOL_MODEL_MAP[tool_name]
        fields = get_numeric_fields(model)
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

    x_metric_label = x_metric.replace("_", " ").title()
    y_metric_label = y_metric.replace("_", " ").title()

    # Build Query
    # 1. Define all columns to be selected
    cols_to_select = []
    df_cols = []
    grouping_args = {"color": None, "symbol": None}

    # Add metric columns for X and Y axes
    if x_model == y_model:
        cols_to_select.extend(
            [
                getattr(x_model, x_metric).label("x"),
                getattr(x_model, y_metric).label("y"),
            ]
        )
    else:
        cols_to_select.extend(
            [
                getattr(x_model, x_metric).label("x"),
                getattr(y_model, y_metric).label("y"),
            ]
        )
    df_cols.extend(["x", "y"])

    # Process unique grouping factors to avoid duplicate columns in the query
    unique_group_vals = {val for val in [color_by, symbol_by] if val}
    for arg_val in unique_group_vals:
        model_name, field_name = arg_val.split(".")
        model = {"run": Run, "sample": Sample, "assay": Assay}.get(model_name)
        if model:
            unique_alias = f"{model_name}_{field_name}"
            cols_to_select.append(getattr(model, field_name).label(unique_alias))
            df_cols.append(unique_alias)

    # Map the selected values back to the plotly arguments
    if color_by:
        grouping_args["color"] = f"{color_by.split('.')[0]}_{color_by.split('.')[1]}"
    if symbol_by:
        grouping_args["symbol"] = f"{symbol_by.split('.')[0]}_{symbol_by.split('.')[1]}"

    # Add hover data columns
    cols_to_select.extend(
        [Sample.name.label("sample_name"), Run.run_folder.label("run_folder")]
    )
    df_cols.extend(["sample_name", "run_folder"])

    # 2. Build the query statement with explicit FROM and JOINs
    stmt = select(*cols_to_select).select_from(Sample)
    stmt = stmt.join(Run, Sample.run_id == Run.id).join(Assay, Run.assay_id == Assay.id)
    stmt = stmt.join(x_model, Sample.id == x_model.sample_id)
    if x_model != y_model:
        stmt = stmt.join(y_model, Sample.id == y_model.sample_id)

    # 3. Add filters
    stmt = stmt.where(Assay.name.in_(assay_names))
    # Add run filter if any are selected
    if run_folders:
        stmt = stmt.where(Run.run_folder.in_(run_folders))
    # Apply sample filter
    if sample_filter == "controls_only":
        stmt = stmt.where(Sample.is_control == True)

    with get_session() as session:
        results = session.exec(stmt).all()

    if not results:
        return create_warning_figure(
            "No data found for the selected combination of metrics."
        )

    df = pd.DataFrame(results, columns=df_cols).dropna(subset=["x", "y"])

    if df.empty:
        return create_warning_figure(
            "No overlapping samples found for the selected metrics."
        )

    df = format_categorical_columns(df, color_by, symbol_by, grouping_args)

    # Apply transformations
    # Filter for log scale first, as it reduces the dataset
    if xaxis_transform == "log":
        df = df[df["x"] > 0]
    if yaxis_transform == "log":
        df = df[df["y"] > 0]

    if df.empty:
        return create_warning_figure(
            "No positive data points remain after applying log scale filter(s)."
        )

    # Apply standardisation
    if xaxis_transform == "standardise":
        mean_val, std_val = df["x"].mean(), df["x"].std()
        if std_val > 0:
            df["x"] = (df["x"] - mean_val) / std_val
        else:
            df["x"] = 0
        x_metric_label = f"{x_metric_label} (Z-score)"

    if yaxis_transform == "standardise":
        mean_val, std_val = df["y"].mean(), df["y"].std()
        if std_val > 0:
            df["y"] = (df["y"] - mean_val) / std_val
        else:
            df["y"] = 0
        y_metric_label = f"{y_metric_label} (Z-score)"

    trendline_arg = trendline if trendline != "none" else None
    fig = px.scatter(
        df,
        x="x",
        y="y",
        color=grouping_args["color"],
        symbol=grouping_args["symbol"],
        hover_name="sample_name",
        custom_data=["run_folder"],
        labels={"x": x_metric_label, "y": y_metric_label},
        title=f"Correlation: {x_metric_label} vs. {y_metric_label}",
        trendline=trendline_arg,
    )

    # Update hovertemplate to explicitly show custom data
    fig.update_traces(
        hovertemplate=(
            f"<b>%{{hovertext}}</b><br><br>"
            f"Run Folder: %{{customdata[0]}}<br>"
            f"{x_metric_label}: %{{x:.3f}}<br>"
            f"{y_metric_label}: %{{y:.3f}}"
            f"<extra></extra>"
        )
    )

    # Add R-squared to title if OLS trendline is used for the whole dataset
    if trendline == "ols" and not grouping_args["color"]:
        try:
            results = px.get_trendline_results(fig)
            r_squared = results.iloc[0]["px_fit_results"].rsquared
            title = fig.layout.title.text
            fig.update_layout(title=f"{title} (R² = {r_squared:.3f})")
        except (IndexError, AttributeError):
            # This can happen if the fit fails. Silently ignore.
            pass

    # Update axes types for log scale after plot creation
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
