from io import StringIO

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dash_table, dcc, html

from app.db import get_session
from data.models.choices import SexKaryotype
from data.plots.summary import create_summary_chart
from data.queries.summary import get_summary_stats

dash.register_page(
    __name__,
    path="/dashboard",
    name="Dashboard",
    description="An overview of summary stats.",
)


def create_summary_datatable(table_id):
    return dash_table.DataTable(
        id=table_id,
        style_cell={"textAlign": "left", "padding": "10px"},
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "rgb(248, 248, 248)"}
        ],
    )


def create_chart_card(title, toggle_id, graph_container_id, default_view="bar"):
    return dbc.Card(
        [
            dbc.CardHeader(
                dbc.Row(
                    [
                        dbc.Col(html.H4(title), width="auto"),
                        dbc.Col(
                            dbc.RadioItems(
                                id=toggle_id,
                                className="btn-group",
                                inputClassName="btn-check",
                                labelClassName="btn btn-outline-secondary btn-sm",
                                labelCheckedClassName="active",
                                options=[
                                    {"label": "Pie", "value": "pie"},
                                    {"label": "Bar", "value": "bar"},
                                ],
                                value=default_view,
                            ),
                            width="auto",
                        ),
                    ],
                    justify="between",
                    align="center",
                )
            ),
            dbc.CardBody(dcc.Loading(children=[html.Div(id=graph_container_id)])),
        ]
    )


layout = dbc.Container(
    [
        dcc.Store(id="dashboard-page-load"),
        dcc.Store(id="runs-per-assay-store"),
        dcc.Store(id="total-sequencer-store"),
        dcc.Store(id="sequencer-summary-store"),
        dcc.Store(id="sex-summary-store"),
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.H1("Verity Dashboard"),
                        html.P("An overview of summary stats.", className="lead"),
                    ],
                    className="mb-4",
                )
            )
        ),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(html.H4("Database Summary by Assay")),
                        dbc.CardBody(
                            dcc.Loading(
                                id="loading-summary-table",
                                children=[create_summary_datatable("summary-table")],
                                type="default",
                            )
                        ),
                    ]
                ),
                md=12,
            ),
            className="mb-4",
        ),
        dbc.Row(
            [
                dbc.Col(
                    create_chart_card(
                        "Runs per Assay",
                        "runs-per-assay-toggle",
                        "runs-per-assay-container",
                    ),
                    md=6,
                ),
                dbc.Col(
                    create_chart_card(
                        "Total Runs per Sequencer",
                        "total-sequencer-toggle",
                        "total-sequencer-container",
                        default_view="pie",
                    ),
                    md=6,
                ),
            ],
            className="mb-4",
        ),
        dbc.Row(
            [
                dbc.Col(
                    create_chart_card(
                        "Runs per Sequencer by Assay",
                        "sequencer-by-assay-toggle",
                        "sequencer-by-assay-container",
                    ),
                    md=6,
                ),
                dbc.Col(
                    create_chart_card(
                        "Sample Sex Distribution by Assay",
                        "sex-by-assay-toggle",
                        "sex-by-assay-container",
                    ),
                    md=6,
                ),
            ],
            className="mb-4",
        ),
    ],
    fluid=True,
    className="mt-4",
)


@callback(
    Output("summary-table", "data"),
    Output("summary-table", "columns"),
    Output("runs-per-assay-store", "data"),
    Output("total-sequencer-store", "data"),
    Output("sequencer-summary-store", "data"),
    Output("sex-summary-store", "data"),
    Input("dashboard-page-load", "data"),
)
def update_home_page_summary(_):
    with get_session() as session:
        (
            summary_results,
            sequencer_results,
            total_sequencer_results,
            sex_results,
        ) = get_summary_stats(session)

    if not summary_results:
        return [], [], None, None, None, None

    df = pd.DataFrame(
        summary_results, columns=["Assay", "Runs", "Samples", "First Run", "Last Run"]
    )
    df_for_chart = df.copy()
    total_row = pd.DataFrame(
        [
            {
                "Assay": "Total",
                "Runs": df["Runs"].sum(),
                "Samples": df["Samples"].sum(),
                "First Run": df[df["First Run"].notna()]["First Run"].min(),
                "Last Run": df[df["Last Run"].notna()]["Last Run"].max(),
            }
        ]
    )
    df = pd.concat([df, total_row], ignore_index=True)
    df["First Run"] = pd.to_datetime(df["First Run"], errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    df["Last Run"] = pd.to_datetime(df["Last Run"], errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    df.fillna("N/A", inplace=True)
    columns = [{"name": i, "id": i} for i in df.columns]
    data = df.to_dict("records")
    total_sequencer_df = pd.DataFrame(
        total_sequencer_results, columns=["sequencer_id", "run_count"]
    )
    sequencer_df = pd.DataFrame(
        sequencer_results, columns=["assay", "sequencer_id", "run_count"]
    )
    sex_df = pd.DataFrame(sex_results, columns=["assay", "sex", "sample_count"])
    return (
        data,
        columns,
        df_for_chart.to_json(orient="split"),
        total_sequencer_df.to_json(orient="split"),
        sequencer_df.to_json(orient="split"),
        sex_df.to_json(orient="split"),
    )


@callback(
    Output("runs-per-assay-container", "children"),
    Input("runs-per-assay-store", "data"),
    Input("runs-per-assay-toggle", "value"),
)
def update_runs_per_assay_chart(data, chart_type):
    if not data:
        return dbc.Alert("No run data available.", color="info")
    df = pd.read_json(StringIO(data), orient="split")
    fig = create_summary_chart(
        df,
        x_col="Assay",
        y_col="Runs",
        title="Total Runs per Assay",
        chart_type=chart_type,
        labels={"Runs": "Number of Runs"},
    )
    return dcc.Graph(figure=fig)


@callback(
    Output("total-sequencer-container", "children"),
    Input("total-sequencer-store", "data"),
    Input("total-sequencer-toggle", "value"),
)
def update_total_sequencer_chart(data, chart_type):
    if not data:
        return dbc.Alert("No sequencer data available.", color="info")
    df = pd.read_json(StringIO(data), orient="split")
    fig = create_summary_chart(
        df,
        x_col="sequencer_id",
        y_col="run_count",
        title="Total Runs per Sequencer",
        chart_type=chart_type,
    )
    return dcc.Graph(figure=fig)


@callback(
    Output("sequencer-by-assay-container", "children"),
    Input("sequencer-summary-store", "data"),
    Input("sequencer-by-assay-toggle", "value"),
)
def update_sequencer_by_assay_tabs(data, chart_type):
    if not data:
        return dbc.Alert("No sequencer data available.", color="info")
    df = pd.read_json(StringIO(data), orient="split")
    sequencer_tabs = []
    unique_sequencer_assays = sorted(df["assay"].unique())
    for assay_name in unique_sequencer_assays:
        assay_df = df[df["assay"] == assay_name]
        if assay_df.empty:
            continue
        sequencer_fig = create_summary_chart(
            assay_df,
            x_col="sequencer_id",
            y_col="run_count",
            title="Runs per Sequencer",
            chart_type=chart_type,
        )
        sequencer_tabs.append(
            dbc.Tab(
                dcc.Graph(figure=sequencer_fig),
                label=assay_name,
                tab_id=assay_name,
            )
        )
    active_tab = unique_sequencer_assays[0] if unique_sequencer_assays else None
    return dbc.Tabs(sequencer_tabs, id="sequencer-tabs", active_tab=active_tab)


@callback(
    Output("sex-by-assay-container", "children"),
    Input("sex-summary-store", "data"),
    Input("sex-by-assay-toggle", "value"),
)
def update_sex_by_assay_tabs(data, chart_type):
    if not data:
        return dbc.Alert("No sample sex data available.", color="info")
    df = pd.read_json(StringIO(data), orient="split")
    sex_tabs = []
    df["sex"] = df["sex"].apply(lambda x: str(SexKaryotype(x)))
    unique_sex_assays = sorted(df["assay"].unique())
    for assay_name in unique_sex_assays:
        assay_df = df[df["assay"] == assay_name]
        if assay_df.empty:
            continue
        sex_fig = create_summary_chart(
            assay_df,
            x_col="sex",
            y_col="sample_count",
            title="Sample Sex Distribution",
            chart_type=chart_type,
        )
        sex_tabs.append(
            dbc.Tab(dcc.Graph(figure=sex_fig), label=assay_name, tab_id=assay_name)
        )
    sex_active_tab = unique_sex_assays[0] if unique_sex_assays else None
    return dbc.Tabs(sex_tabs, id="sex-tabs", active_tab=sex_active_tab)
