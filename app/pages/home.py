import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

dash.register_page(__name__, path="/", name="Home")


def create_overview_card(title, description, href=None, status=None, icon=None):
    """Create a linked module card or a non-interactive status card."""
    heading = html.Div(
        [
            html.H3(title, className="h5 mb-0"),
            dbc.Badge(status, color="warning", className="ms-2") if status else None,
        ],
        className="d-flex align-items-center",
    )
    card = dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        (
                            html.I(className=f"bi {icon} fs-2 text-primary")
                            if icon
                            else None
                        ),
                        heading,
                    ],
                    className="d-flex align-items-center gap-3 mb-3",
                ),
                html.P(description, className="text-muted mb-0"),
            ]
        ),
        className="h-100 shadow-sm",
        style={"minHeight": "190px"},
    )
    if href:
        return dcc.Link(card, href=href, className="text-decoration-none h-100")
    return card


pages = [
    {
        "title": "Dashboard",
        "description": "An overview of summary stats.",
        "href": "/dashboard",
        "status": "Beta",
        "icon": "bi-speedometer2",
    },
    {
        "title": "Raincloud Plot",
        "description": "Compare metric distributions across selected runs.",
        "href": "/plot",
        "status": "Beta",
        "icon": "bi-cloud-rain",
    },
    {
        "title": "Metric Trends",
        "description": "Track sample- and run-level metrics over recent runs.",
        "href": "/trends",
        "icon": "bi-graph-up-arrow",
    },
    {
        "title": "Correlation",
        "description": "Compare relationships between metrics and runs.",
        "href": "/correlation",
        "icon": "bi-diagram-3",
    },
    {
        "title": "Explore Data",
        "description": "Inspect and filter the raw QC data in the database.",
        "href": "/explore",
        "icon": "bi-search",
    },
    {
        "title": "Run level metrics",
        "description": "Detailed metrics for individual sequencing runs.",
        "status": "Coming soon",
        "icon": "bi-bar-chart-line",
    },
]


layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("Welcome to Verity", className="display-5 fw-bold"),
                html.P(
                    "Choose a module to explore MultiQC data.",
                    className="lead text-muted",
                ),
            ],
            className="py-4",
        ),
        dbc.Row(
            [
                dbc.Col(
                    create_overview_card(**page),
                    xs=12,
                    md=6,
                    lg=4,
                    className="mb-4",
                )
                for page in pages
            ]
        ),
    ],
    fluid=True,
    className="mt-2",
)
