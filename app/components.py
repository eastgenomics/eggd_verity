import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html


def create_warning_figure(message, height=None):
    """Creates an empty figure with a warning message."""
    fig = go.Figure()
    fig.update_layout(
        height=height,
        xaxis_visible=False,
        yaxis_visible=False,
        paper_bgcolor="#fff3cd",
        plot_bgcolor="#fff3cd",
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 16, "color": "#664d03"},
            }
        ],
    )
    return fig


def create_plot_page_layout(controls_component, graph_id, hover_box_id, page_title):
    """
    Creates the standard two-column layout for a plot page.
    """
    return dbc.Container(
        [
            html.H2(page_title),
            dbc.Row(
                [
                    dbc.Col(controls_component, md=3),
                    dbc.Col(
                        [
                            dcc.Loading(
                                id=f"loading-{graph_id}",
                                children=[dcc.Graph(id=graph_id)],
                                type="default",
                            ),
                            html.Div(
                                id=hover_box_id,
                                className="mt-2 p-2 border rounded bg-light",
                                style={"minHeight": "100px"},
                            ),
                        ],
                        md=9,
                    ),
                ]
            ),
        ],
        fluid=True,
    )


def create_sample_filter_control():
    """Creates the radio button control for filtering sample types."""
    return dbc.Container(
        dbc.RadioItems(
            id="sample-filter-radio",
            className="btn-group",
            inputClassName="btn-check",
            labelClassName="btn btn-outline-primary",
            labelCheckedClassName="active",
            options=[
                {"label": "All Samples", "value": "all"},
                {"label": "Control Samples Only", "value": "controls_only"},
            ],
            value="all",  # Default value
        ),
        className="radio-group mb-4 d-flex justify-content-center",
    )
