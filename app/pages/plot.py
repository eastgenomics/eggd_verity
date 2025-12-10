import re
from urllib.parse import parse_qs, urlencode, urlparse

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html, no_update
from sqlmodel import select

from app.components import create_sample_filter_control, create_warning_figure
from app.db import get_session
from app.plot_utils import format_categorical_columns, register_hover_callbacks
from app.utils import get_metric_models, get_numeric_fields, get_plot_grouping_options
from data.models.reports import Assay, Run, Sample

dash.register_page(__name__, path="/plot", name="Raincloud Plot")

TOOL_MODEL_MAP = get_metric_models()


controls = dbc.Card(
    [
        dbc.Label("1. Select Assay(s)", className="fw-bold"),
        dcc.Dropdown(
            id="plot-assay-dropdown",
            placeholder="Select one or more assays...",
            multi=True,
        ),
        dbc.Label("2. Select QC Tool", className="fw-bold mt-2"),
        dcc.Dropdown(id="plot-tool-dropdown", placeholder="Select a tool..."),
        dbc.Label("3. Select Metric", className="fw-bold mt-2"),
        dcc.Dropdown(id="plot-metric-dropdown", placeholder="Select a metric..."),
        dbc.Label("4. Number of Runs", className="fw-bold mt-2"),
        dcc.Input(
            id="plot-num-runs-input",
            type="number",
            min=1,
            max=100,
            value=10,
            placeholder="Enter number of runs...",
        ),
        dbc.Label("5. Sample Name Filter (Regex)", className="fw-bold mt-2"),
        dcc.Input(
            id="plot-sample-filter-input",
            type="text",
            placeholder="Enter regex pattern...",
        ),
        html.Br(),
        dbc.Label("6. Colour By", className="fw-bold mt-2"),
        dcc.Dropdown(id="plot-color-by-dropdown", placeholder="Select a category..."),
        html.Hr(),
        dbc.Label("7. Customise Plot Elements", className="fw-bold mt-2"),
        html.Br(),
        dbc.Label("Violin Side", className="mt-2"),
        dbc.RadioItems(
            id="plot-violin-side-radio",
            options=[
                {"label": "Right", "value": "positive"},
                {"label": "Left", "value": "negative"},
                {"label": "Both", "value": "both"},
            ],
            value="positive",
            inline=True,
        ),
        dbc.Label("Visible Elements", className="mt-2"),
        dbc.Checklist(
            id="plot-components-checklist",
            options=[
                {"label": "Violin (Cloud)", "value": "violin"},
                {"label": "Box Plot", "value": "box"},
                {"label": "Points (Rain)", "value": "points"},
            ],
            value=["violin", "box", "points"],
            inline=True,
        ),
    ],
    body=True,
    className="mb-4",
)


def create_plot_page_layout(controls_component, plot_id, hover_data_box_id, title):
    """
    Creates a standard layout for a plot page with a collapsible sidebar for controls.
    """
    return dbc.Container(
        [
            dbc.Offcanvas(
                controls_component,
                id="plot-offcanvas-controls",
                title="Plot Controls",
                is_open=True,
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Button(
                            "⚙️ Controls", id="plot-open-offcanvas-button", n_clicks=0
                        ),
                        width="auto",
                    ),
                    dbc.Col(html.H2(title), width="auto"),
                    dbc.Col(
                        html.Pre(id=hover_data_box_id, className="text-white"),
                        width="auto",
                    ),
                ],
                align="center",
            ),
            dbc.Row([dbc.Col(dcc.Graph(id=plot_id, style={"height": "75vh"}))]),
        ],
        fluid=True,
    )


# Callbacks

register_hover_callbacks("plot")


@callback(
    Output("plot-offcanvas-controls", "is_open"),
    Input("plot-open-offcanvas-button", "n_clicks"),
    [State("plot-offcanvas-controls", "is_open")],
)
def toggle_offcanvas(n1, is_open):
    if n1:
        return not is_open
    return is_open


@callback(Output("plot-assay-dropdown", "options"), Input("plot-assay-dropdown", "id"))
def populate_assays(_):
    """Populates the assay dropdown with all available assay names."""
    with get_session() as session:
        assays = session.exec(select(Assay.name).distinct()).all()
        return sorted(assays)


@callback(Output("plot-tool-dropdown", "options"), Input("plot-tool-dropdown", "id"))
def populate_tools(_):
    """Populates the tool dropdown with all discovered metric models."""
    return list(TOOL_MODEL_MAP.keys())


@callback(
    Output("plot-metric-dropdown", "options"), Input("plot-tool-dropdown", "value")
)
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


@callback(
    Output("plot-color-by-dropdown", "options"), Input("plot-color-by-dropdown", "id")
)
def populate_grouping_options(_):
    """Populates the 'Color By' dropdown."""
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
    return formatted_options


def _create_violin_trace(df, metric_name, side, color_map, color_col):
    """Creates violin traces for the plot."""
    traces = []
    for i, run in enumerate(df["run_folder"].unique()):
        df_run = df[df["run_folder"] == run]
        traces.append(
            go.Violin(
                x=df_run["run_folder"],
                y=df_run[metric_name],
                name=run,
                side=side if side != "both" else None,
                width=0.8,
                line_color=(
                    color_map.get(df_run[color_col].iloc[0])
                    if color_col != "run_folder"
                    else color_map.get(run)
                ),
                showlegend=False,
            )
        )
    return traces


def _create_box_trace(df, metric_name, side, color_map, color_col):
    """Creates box plot traces, positioned correctly relative to the violin."""
    traces = []
    # Adjust offset based on violin side to keep it centered in the half-violin
    offset_map = {"positive": 0.15, "negative": -0.15, "both": 0}
    offset = offset_map.get(side, 0)

    for i, run in enumerate(df["run_folder"].unique()):
        df_run = df[df["run_folder"] == run]
        traces.append(
            go.Box(
                x=df_run["run_folder"],
                y=df_run[metric_name],
                name=run,
                marker_color=(
                    color_map.get(df_run[color_col].iloc[0])
                    if color_col != "run_folder"
                    else color_map.get(run)
                ),
                boxpoints=False,
                width=0.15,
                offsetgroup=f"{run}_box",
                x0=offset,
                showlegend=False,
                boxmean=True,
            )
        )
    return traces


def _create_strip_trace(df, metric_name, side, color_map, color_col):
    """Creates strip plot (point) traces."""
    traces = []
    # Adjust point position based on violin side
    pointpos_map = {"positive": -0.6, "negative": 0.6, "both": 0}
    pointpos = pointpos_map.get(side, 0)

    for i, run in enumerate(df["run_folder"].unique()):
        df_run = df[df["run_folder"] == run]
        traces.append(
            go.Box(
                x=df_run["run_folder"],
                y=df_run[metric_name],
                name=run,
                boxpoints="all",
                jitter=0.2,
                pointpos=pointpos,
                marker_color=(
                    color_map.get(df_run[color_col].iloc[0])
                    if color_col != "run_folder"
                    else color_map.get(run)
                ),
                marker=dict(size=3, opacity=0.6),
                line_width=0,
                fillcolor="rgba(0,0,0,0)",
                hoverinfo="y+name",
                showlegend=False,
                width=0.7,
            )
        )
    return traces


@callback(
    Output("raincloud-plot", "figure"),
    [
        Input("plot-assay-dropdown", "value"),
        Input("plot-tool-dropdown", "value"),
        Input("plot-metric-dropdown", "value"),
        Input("plot-num-runs-input", "value"),
        Input("plot-sample-filter-input", "value"),
        Input("plot-color-by-dropdown", "value"),
        Input("plot-violin-side-radio", "value"),
        Input("plot-components-checklist", "value"),
    ],
)
def update_raincloud_plot(
    assay_names,
    tool_name,
    metric_name,
    num_runs,
    sample_filter,
    color_by,
    violin_side,
    plot_components,
):
    """Updates the raincloud plot based on user selections."""
    if not all([assay_names, tool_name, metric_name]):
        return create_warning_figure(
            "Please select at least one assay, a tool, and a metric to plot."
        )

    tool_model = TOOL_MODEL_MAP[tool_name]

    is_run_level = tool_model.metric_level == "run"

    # Columns to select from the database
    columns_to_select = [
        Run.date,
        Run.run_folder.label("run_folder"),
        getattr(tool_model, metric_name).label(metric_name),
    ]
    df_cols = ["date", "run_folder", metric_name]

    if not is_run_level:
        columns_to_select.append(Sample.name.label("sample_name"))
        df_cols.append("sample_name")

    # Add color_by column if selected
    grouping_args = {"color": None}
    if color_by:
        model_name, field_name = color_by.split(".")
        if model_name == "run":
            model = Run
        elif model_name == "sample":
            model = Sample
        elif model_name == "assay":
            model = Assay
        else:
            model = None
        if model:
            unique_alias = f"{model_name}_{field_name}"
            columns_to_select.append(getattr(model, field_name).label(unique_alias))
            df_cols.append(unique_alias)
            grouping_args["color"] = unique_alias

    with get_session() as session:
        # Subquery to find the most recent N runs for the given assays
        latest_runs_stmt = (
            select(Run.id)
            .join(Assay, Run.assay_id == Assay.id)
            .where(Assay.name.in_(assay_names))
            .order_by(Run.date.desc())  # Get the N most recent runs
            .limit(num_runs)
        ).alias("latest_runs")

        if is_run_level:
            statement = select(*columns_to_select).join(
                tool_model, Run.id == tool_model.run_id
            )
        else:
            statement = (
                select(*columns_to_select)
                .join(Sample, Run.id == Sample.run_id)
                .join(tool_model, Sample.id == tool_model.sample_id)
            )

        # Common joins and filters for both run and sample level
        statement = statement.join(Assay, Run.assay_id == Assay.id).join(
            latest_runs_stmt, Run.id == latest_runs_stmt.c.id
        )

        results = session.exec(statement).all()

    if not results:
        return create_warning_figure(
            f"No data found for the selected metrics in the selected assays."
        )

    df = pd.DataFrame(results, columns=df_cols)
    # Convert to date objects to remove the time component from the axis
    df = df.sort_values("date", ascending=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # For run-level metrics, create a placeholder 'sample_name' column
    # for consistent hover information.
    if is_run_level:
        df["sample_name"] = df["run_folder"]

    # Apply sample name filter if provided
    if sample_filter:
        try:
            df = df[df["sample_name"].str.contains(sample_filter, regex=True)]
        except re.error:
            return create_warning_figure(
                "Invalid regex pattern. Please correct the sample name filter."
            )

    ordered_runs = df["run_folder"].unique()

    df = format_categorical_columns(df, color_by, None, grouping_args)

    # Determine the column to use for colouring
    color_col = grouping_args["color"]
    color_discrete_map = None

    # Default to colouring by run_folder if no other option is chosen
    if not color_col or color_col == "run_run_folder":
        color_col = "run_folder"
        unique_runs = df["run_folder"].unique()
        color_discrete_map = {
            run: color for run, color in zip(unique_runs, px.colors.qualitative.Plotly)
        }
    else:
        # If coloring by another category, create a map for go.Figure
        unique_colors = df[color_col].unique()
        color_discrete_map = {
            cat: color
            for cat, color in zip(unique_colors, px.colors.qualitative.Plotly)
        }
        df["color"] = df[color_col].map(color_discrete_map)

    fig = go.Figure()

    # Add traces based on user selection
    if "violin" in plot_components:
        for trace in _create_violin_trace(
            df, metric_name, violin_side, color_discrete_map, color_col
        ):
            fig.add_trace(trace)
    if "box" in plot_components:
        for trace in _create_box_trace(
            df, metric_name, violin_side, color_discrete_map, color_col
        ):
            fig.add_trace(trace)
    if "points" in plot_components:
        for trace in _create_strip_trace(
            df,
            metric_name,
            violin_side,
            color_discrete_map,
            color_col,
        ):
            fig.add_trace(trace)

    metric_title = metric_name.replace("_", " ").title()
    plot_title = f"{tool_name}: {metric_title} for the last {num_runs} run(s)"

    fig.update_layout(
        title=plot_title,
        title_font=dict(size=20, family="Arial", color="black"),
        violingap=0,
        violinmode="overlay",
        xaxis_tickangle=-45,
        xaxis=dict(categoryorder="array", categoryarray=ordered_runs),
        showlegend=True if grouping_args["color"] else False,
        yaxis_title=metric_name.replace("_", " ").title(),
        xaxis_title="Run",
    )
    return fig


def layout(
    assay: list[str] | str | None = None,
    tool: str | None = None,
    metric: str | None = None,
    num_runs: int = 10,
    sample_filter: str | None = None,
    color_by: str | None = None,
    violin_side: str = "positive",
    plot_components: list[str] | None = None,
    **_,
):
    """
    Defines the layout for the plot page, accepting query parameters to set
    the initial state of the controls.
    """
    # Set default values for multi-select checklists
    if plot_components is None:
        plot_components = ["violin", "box", "points"]

    # Ensure assay is a list for multi-select dropdown
    if isinstance(assay, str):
        assay = [assay]

    # Find the controls in the tree and update their values
    for child in controls.children:
        if not hasattr(child, "id"):
            continue

        if child.id == "plot-assay-dropdown":
            child.value = assay
        elif child.id == "plot-tool-dropdown":
            child.value = tool
        elif child.id == "plot-metric-dropdown":
            child.value = metric
        elif child.id == "plot-num-runs-input":
            child.value = num_runs
        elif child.id == "plot-sample-filter-input":
            child.value = sample_filter
        elif child.id == "plot-color-by-dropdown":
            child.value = color_by
        elif child.id == "plot-violin-side-radio":
            child.value = violin_side
        elif child.id == "plot-components-checklist":
            child.value = plot_components

    page_layout = html.Div(
        [
            dcc.Location(id="plot-url", refresh=False),
            create_plot_page_layout(
                controls, "raincloud-plot", "plot-hover-data-box", "Raincloud Plot"
            ),
        ]
    )
    return page_layout


@callback(
    Output("plot-url", "search"),
    [
        Input("plot-assay-dropdown", "value"),
        Input("plot-tool-dropdown", "value"),
        Input("plot-metric-dropdown", "value"),
        Input("plot-num-runs-input", "value"),
        Input("plot-sample-filter-input", "value"),
        Input("plot-color-by-dropdown", "value"),
        Input("plot-violin-side-radio", "value"),
        Input("plot-components-checklist", "value"),
    ],
    prevent_initial_call=True,
)
def update_url(
    assay,
    tool,
    metric,
    num_runs,
    sample_filter,
    color_by,
    violin_side,
    plot_components,
):
    """Updates the URL query string based on the selected plot options."""
    query_params = {
        "assay": assay or [],
        "tool": tool or "",
        "metric": metric or "",
        "num_runs": num_runs or 10,
        "sample_filter": sample_filter or "",
        "color_by": color_by or "",
        "violin_side": violin_side or "positive",
        "plot_components": plot_components or [],
    }
    encoded_params = urlencode(query_params, doseq=True)
    return f"?{encoded_params}"


@callback(
    Output("plot-offcanvas-controls", "is_open", allow_duplicate=True),
    Input("raincloud-plot", "figure"),
    State("plot-offcanvas-controls", "is_open"),
    prevent_initial_call=True,
)
def close_offcanvas(_figure, is_open):
    """
    Closes the offcanvas sidebar only when a valid plot is generated.
    It inspects the figure to see if it's a warning figure and, if so,
    keeps the sidebar open.
    """
    if not is_open or not _figure:
        return no_update

    if _figure.get("layout", {}).get("paper_bgcolor") == "#fff3cd":
        return no_update

    return False
    return False
