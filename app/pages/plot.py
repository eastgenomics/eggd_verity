from urllib.parse import parse_qs, urlencode, urlparse

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update

from app.components import create_warning_figure
from app.db import get_session
from app.utils import register_hover_callbacks
from data.plots.raincloud import create_raincloud_figure
from data.queries.general import get_assay_names, get_available_tools
from data.queries.raincloud import get_raincloud_data
from data.utils.model_utils import get_metric_models, get_plot_grouping_options

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

    with get_session() as session:
        df, grouping_args = get_raincloud_data(
            session,
            assay_names,
            tool_model,
            metric_name,
            num_runs,
            color_by,
        )

    if df.empty:
        return create_warning_figure(
            f"No data found for the selected metrics in the selected assays."
        )

    # Apply sample name filter if provided
    if sample_filter:
        try:
            df = df[df["sample_name"].str.contains(sample_filter, regex=True)]
        except Exception:
            return create_warning_figure(
                "Invalid regex pattern. Please correct the sample name filter."
            )

    return create_raincloud_figure(
        df,
        tool_name,
        metric_name,
        num_runs,
        grouping_args["color"],
        violin_side,
        plot_components,
    )


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
