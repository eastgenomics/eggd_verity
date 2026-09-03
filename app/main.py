import dash
import dash_auth
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, callback, dcc, html

from app.config import settings

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css",
        "https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&display=swap",
    ],
    suppress_callback_exceptions=True,
)
server = app.server
server.secret_key = settings.SECRET_KEY


def configure_auth(app, settings):
    """Attach Basic Auth when it is enabled in application settings."""
    if settings.AUTH_ENABLED:
        credentials = {settings.USERNAME: settings.PASSWORD}
        return dash_auth.BasicAuth(app, credentials)
    return None


auth = configure_auth(app, settings)

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Dashboard", href="/dashboard")),
        dbc.NavItem(dbc.NavLink("Trends", href="/trends")),
        dbc.NavItem(dbc.NavLink("Raincloud", href="/plot")),
        dbc.NavItem(dbc.NavLink("Correlation", href="/correlation")),
        dbc.NavItem(dbc.NavLink("Explore Data", href="/explore")),
    ],
    brand=html.Span(
        "Verity",
        style={
            "fontFamily": "'DM Serif Display', Georgia, serif",
            "fontSize": "1.8rem",
            "fontStyle": "italic",
            "letterSpacing": "0.04em",
        },
    ),
    brand_href="/",
    color="primary",
    dark=True,
    className="mb-4",
)

# Main app layout
app.layout = html.Div(
    [
        dcc.Store(id="sample-filter-store", storage_type="session"),
        navbar,
        dash.page_container,
    ],
    style={"backgroundColor": "#f8f9fa"},
)


@callback(Output("sample-filter-store", "data"), Input("sample-filter-radio", "value"))
def update_sample_filter_store(value):
    return value


if __name__ == "__main__":
    app.run(debug=True)
