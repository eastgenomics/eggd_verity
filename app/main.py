import dash
import dash_auth
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, callback, dcc, html

from app.config import settings

VALID_USERNAME_PASSWORD_PAIRS = {settings.USERNAME: settings.PASSWORD}

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
server = app.server
server.secret_key = settings.SECRET_KEY

auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Home", href="/")),
        dbc.NavItem(dbc.NavLink("Trends", href="/trends")),
        dbc.NavItem(dbc.NavLink("Plot", href="/plot")),
        dbc.NavItem(dbc.NavLink("Correlation", href="/correlation")),
        dbc.NavItem(dbc.NavLink("Explore Data", href="/explore")),
    ],
    brand="Verity QC Audit",
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
