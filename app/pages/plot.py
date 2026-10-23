from urllib.parse import parse_qs, urlencode, urlparse

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update

from app.components import create_plot_warnings, create_warning_figure
from app.db import get_session
from app.utils import register_hover_callbacks
from data.plots.raincloud import create_raincloud_figure
from data.queries.general import get_assay_names, get_available_tools
from data.queries.raincloud import get_raincloud_data
from data.queries.warnings import get_plot_warnings
from data.utils.model_utils import get_metric_models, get_plot_grouping_options

dash.register_page(__name__, path="/plot", name="Raincloud Plot")

TOOL_MODEL_MAP = get_metric_models()


DEFAULT_COLOR_BY = "run.sequencer_id"
DEFAULT_PLOT_COMPONENTS = ["violin", "box", "points"]


def create_controls(
    assay=None,
    tool=None,
    metric=None,
    num_runs=10,
    sample_filter=None,
    color_by=DEFAULT_COLOR_BY,
    violin_side="positive",
    plot_components=DEFAULT_PLOT_COMPONENTS,
):
    """
    Builds the controls card with the given initial values. Built per request so
    that one user's URL parameters never leak into another user's page.
    """
    return dbc.Card(
        [
            dbc.Label("1. Select Assay(s)", className="fw-bold"),
            dcc.Dropdown(
                id="plot-assay-dropdown",
                placeholder="Select one or more assays...",
                multi=True,
                value=assay,
            ),
            dbc.Label("2. Select QC Tool", className="fw-bold mt-2"),
            dcc.Dropdown(
                id="plot-tool-dropdown", placeholder="Select a tool...", value=tool
            ),
            dbc.Label("3. Select Metric", className="fw-bold mt-2"),
            dcc.Dropdown(
                id="plot-metric-dropdown",
                placeholder="Select a metric...",
                value=metric,
            ),
            dbc.Label("4. Number of Runs", className="fw-bold mt-2"),
            dcc.Input(
                id="plot-num-runs-input",
                type="number",
                min=1,
                max=100,
                value=num_runs,
                placeholder="Enter number of runs...",
            ),
            dbc.Label("5. Sample Name Filter (Regex)", className="fw-bold mt-2"),
            dcc.Input(
                id="plot-sample-filter-input",
                type="text",
                placeholder="Enter regex pattern...",
                value=sample_filter or "",
            ),
            html.Br(),
            dbc.Label("6. Colour By", className="fw-bold mt-2"),
            dcc.Dropdown(
                id="plot-color-by-dropdown",
                placeholder="Colour by run",
                value=color_by,
            ),
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
                value=violin_side,
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
                value=plot_components,
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
                    dbc.Col(html.H3(title, className="mb-0"), width="auto"),
                    # Hover details sit at the right end of the title row. The
                    # fixed height fits five lines, so the plot below does not
                    # jump when the content changes.
                    dbc.Col(
                        html.Div(
                            id=hover_data_box_id,
                            style={
                                "fontSize": "0.85rem",
                                "height": "5.6rem",
                                "overflow": "hidden",
                            },
                        ),
                        width="auto",
                        className="ms-auto",
                    ),
                ],
                align="center",
                className="mb-1",
            ),
            html.Div(id="plot-warnings"),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(
                            id=plot_id,
                            # Fill the viewport below the navbar and title row
                            style={"height": "calc(100vh - 210px)", "minHeight": "450px"},
                        )
                    )
                ]
            ),
        ],
        fluid=True,
    )


# Callbacks

register_hover_callbacks("plot", graph_id="raincloud-plot", extra_labels=("Assay",))


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
        return get_assay_names(session)


@callback(
    Output("plot-tool-dropdown", "options"), Input("plot-assay-dropdown", "value")
)
def populate_tools(assay_names):
    """Populates the tool dropdown based on selected assays."""
    if not assay_names:
        return []
    with get_session() as session:
        return get_available_tools(session, assay_names, TOOL_MODEL_MAP)


@callback(
    Output("plot-metric-dropdown", "options"), Input("plot-tool-dropdown", "value")
)
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


@callback(
    Output("plot-color-by-dropdown", "options"), Input("plot-tool-dropdown", "value")
)
def populate_grouping_options(tool_name):
    """
    Populates the 'Color By' dropdown. Sample fields are left out for run level
    tools, which have no per sample values.
    """
    options = get_plot_grouping_options()
    if tool_name and TOOL_MODEL_MAP[tool_name].metric_level == "run":
        options.pop("Sample", None)

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


def _warning_only(message: str):
    """A warning figure in place of the plot, with no plot warnings."""
    return create_warning_figure(message), []


@callback(
    Output("raincloud-plot", "figure"),
    Output("plot-warnings", "children"),
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
    """Updates the raincloud plot and its warnings based on user selections."""
    if not all([assay_names, tool_name, metric_name]):
        return _warning_only(
            "Please select at least one assay, a tool, and a metric to plot."
        )

    tool_model = TOOL_MODEL_MAP[tool_name]

    with get_session() as session:
        df, grouping_args = get_raincloud_data(
            session,
            assay_names,
            tool_model,
            metric_name,
            num_runs,
            color_by,
        )
        warnings = get_plot_warnings(session, df, tool_model, num_runs)

    if df.empty:
        return _warning_only(
            f"No data found for the selected metrics in the selected assays."
        )

    # Apply sample name filter if provided
    if sample_filter:
        try:
            df = df[
                df["sample_name"].str.contains(sample_filter, regex=True, na=False)
            ]
        except Exception:
            return _warning_only(
                "Invalid regex pattern. Please correct the sample name filter."
            )
        if df.empty:
            return _warning_only(
                "No samples match the sample name filter."
            )

    color_label = None
    if grouping_args["color"]:
        model_name, field_name = color_by.split(".")
        color_label = f"{model_name.title()}: {field_name.replace('_', ' ').title()}"

    figure = create_raincloud_figure(
        df,
        tool_name,
        metric_name,
        num_runs,
        grouping_args["color"],
        violin_side,
        plot_components,
        color_label,
        assay_names,
    )
    return figure, create_plot_warnings(warnings)


def layout(
    assay: list[str] | str | None = None,
    tool: str | None = None,
    metric: str | None = None,
    num_runs: int | str | None = 10,
    sample_filter: str | None = None,
    color_by: str | None = DEFAULT_COLOR_BY,
    violin_side: str = "positive",
    plot_components: list[str] | str | None = None,
    **_,
):
    """
    Defines the layout for the plot page, accepting query parameters to set
    the initial state of the controls.
    """
    # Query parameters arrive as strings, or as a list when a key repeats
    if plot_components is None:
        plot_components = DEFAULT_PLOT_COMPONENTS
    elif isinstance(plot_components, str):
        plot_components = [plot_components]
    # An empty value in the URL means every element was unchecked
    plot_components = [c for c in plot_components if c]

    if isinstance(assay, str):
        assay = [assay]

    try:
        num_runs = int(num_runs) if num_runs not in (None, "") else None
    except ValueError:
        num_runs = 10

    page_layout = html.Div(
        [
            dcc.Location(id="plot-url", refresh=False),
            create_plot_page_layout(
                create_controls(
                    assay=assay,
                    tool=tool,
                    metric=metric,
                    num_runs=num_runs,
                    sample_filter=sample_filter,
                    color_by=color_by or None,
                    violin_side=violin_side,
                    plot_components=plot_components,
                ),
                "raincloud-plot",
                "plot-hover-data-box",
                "Raincloud Plot",
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
        # An empty value keeps "everything unchecked" through a reload
        "plot_components": plot_components or [""],
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
