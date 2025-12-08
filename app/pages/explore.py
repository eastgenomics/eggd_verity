import json

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dash_table, dcc, html
from sqlmodel import select

from app.db import get_session
from app.utils import get_metric_models
from data.models.choices import QCStatus, SexKaryotype
from data.models.reports import Assay, Run, Sample

dash.register_page(__name__, path="/explore", name="Explore Data")

# Dynamically get models from the utils function
METRIC_MODEL_MAP = get_metric_models()


def create_datatable(table_id, data=None, columns=None):
    """Helper function to create a styled and interactive DataTable."""
    if data is None:
        data = []
    if columns is None:
        columns = []

    return dash_table.DataTable(
        id=table_id,
        columns=columns,
        data=data,
        page_size=5,
        page_action="native",
        filter_action="native",
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_cell={
            "height": "auto",
            "minWidth": "100px",
            "width": "100px",
            "maxWidth": "180px",
            "whiteSpace": "normal",
            "textAlign": "left",
        },
        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"},
    )


layout = dbc.Container(
    [
        dcc.Store(id="selected-run-id-store"),
        html.H2("Explore Database Records"),
        html.P("Follow the steps below to browse the raw QC data for any run."),
        # Step 1: Assay Selection
        dbc.Card(
            [
                dbc.CardHeader(html.H4("Step 1: Select an Assay")),
                dbc.CardBody(
                    [
                        dcc.Dropdown(
                            id="explore-assay-dropdown",
                            placeholder="Select an assay...",
                        ),
                    ]
                ),
            ],
            className="mb-4",
        ),
        # Step 2: Run Selection
        dbc.Card(
            [
                dbc.CardHeader(html.H4("Step 2: Select a Run"), id="run-card-header"),
                dbc.CardBody(dbc.Spinner(html.Div(id="run-table-container"))),
            ],
            className="mb-4",
        ),
        # Step 3: Metric Data
        dbc.Card(
            [
                dbc.CardHeader(html.H4("Step 3: View Metric Data")),
                dbc.CardBody(
                    [
                        dbc.Label("Select a metric type to view its data:"),
                        dbc.Spinner(html.Div(id="metric-selection-container")),
                        html.Hr(),
                        dbc.Spinner(html.Div(id="metric-details-container")),
                    ]
                ),
            ],
        ),
    ],
    fluid=True,
)

# Callbacks


@callback(
    Output("explore-assay-dropdown", "options"),
    Input("explore-assay-dropdown", "id"),  # Trigger on page load
)
def populate_assay_dropdown(_):
    """Populates the assay dropdown with all available assay names."""
    with get_session() as session:
        assays = session.exec(select(Assay.name).distinct()).all()
    return sorted(assays)


@callback(
    Output("run-card-header", "children"),
    Output("run-table-container", "children"),
    Input("explore-assay-dropdown", "value"),
)
def update_assay_info_and_runs_table(assay_name):
    """When an assay is selected, show its info and populate the Runs table."""
    default_header = html.H4("Step 2: Select a Run")
    if not assay_name:
        return default_header, dbc.Alert(
            "Select an assay to see its runs.", color="info"
        )

    with get_session() as session:
        # Fetch the first assay that matches the name.
        assay_obj = session.exec(select(Assay).where(Assay.name == assay_name)).first()
        if not assay_obj:
            return default_header, dbc.Alert(
                f"Assay '{assay_name}' not found.", color="warning"
            )
        runs = session.exec(select(Run).where(Run.assay_id == assay_obj.id)).all()

    assay_details = html.Div(
        [
            html.Span(f"Ref Genome: {assay_obj.ref_genome}", className="me-3"),
        ],
        className="text-muted small",
    )
    new_header = dbc.Row(
        [
            dbc.Col(html.H4("Step 2: Select a Run"), width="auto"),
            dbc.Col(assay_details, width="auto"),
        ],
        justify="between",
        align="center",
    )

    if not runs:
        return new_header, dbc.Alert(f"No runs found for {assay_name}", color="warning")

    df = pd.DataFrame([run.model_dump() for run in runs])

    # Convert QC status enum to string
    df["qc_status"] = df["qc_status"].apply(lambda x: str(QCStatus(x)))

    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # Keep the 'id' column in the data but don't create a visible column for it
    df = df.drop(columns=["assay_id"])
    display_columns = [col for col in df.columns if col != "id"]
    columns = [
        {"name": col.replace("_", " ").title(), "id": col} for col in display_columns
    ]
    run_table = create_datatable("run-table", df.to_dict("records"), columns)
    return new_header, run_table


@callback(
    Output("metric-selection-container", "children"),
    Output("selected-run-id-store", "data"),
    Input("run-table", "active_cell"),
)
def update_metric_selection(active_cell):
    """When a run is clicked, find which metrics are available and show buttons."""
    if not active_cell:
        return dbc.Alert("Select a run to see available metrics.", color="info"), None

    run_id = active_cell["row_id"]
    available_metrics = []
    with get_session() as session:
        for name, model in METRIC_MODEL_MAP.items():
            # Check for run-level metrics
            if model.metric_level == "run":
                exists_stmt = select(model.id).where(model.run_id == run_id).limit(1)
                if session.exec(exists_stmt).first():
                    available_metrics.append(name)
            # Check for sample-level metrics
            else:
                exists_stmt = (
                    select(model.id)
                    .join(Sample)
                    .where(Sample.run_id == run_id)
                    .limit(1)
                )
                if session.exec(exists_stmt).first():
                    available_metrics.append(name)

    if not available_metrics:
        return dbc.Alert("No metric data found for this run.", color="warning"), run_id

    radio_items = dbc.RadioItems(
        id="metric-radio-items",
        className="btn-group",
        inputClassName="btn-check",
        labelClassName="btn btn-outline-primary",
        labelCheckedClassName="active",
        options=[{"label": name, "value": name} for name in available_metrics],
    )
    return html.Div(radio_items, className="d-grid gap-2 d-md-flex"), run_id


@callback(
    Output("metric-details-container", "children"),
    Input("metric-radio-items", "value"),
    State("selected-run-id-store", "data"),
)
def update_metric_details_table(metric_name, run_id):
    """When a metric type is selected, display its data for the selected run."""
    if not metric_name or not run_id:
        return dbc.Alert("Select a metric type to view its data.", color="info")

    tool_model = METRIC_MODEL_MAP[metric_name]
    with get_session() as session:
        if tool_model.metric_level == "run":
            statement = select(tool_model).where(tool_model.run_id == run_id)
            results = session.exec(statement).all()
        else:
            statement = (
                select(Sample.name, tool_model)
                .join(tool_model)
                .where(Sample.run_id == run_id)
            )
            results = session.exec(statement).all()

    if not results:
        return dbc.Alert(f"No {metric_name} data found for this run.", color="warning")

    data = []
    if tool_model.metric_level == "run":
        for metric_obj in results:
            row = metric_obj.model_dump(exclude={"run"})
            data.append(row)
    else:
        for sample_name, metric_obj in results:
            row = metric_obj.model_dump(exclude={"sample"})
            row["sample_name"] = sample_name
            data.append(row)

    df = pd.DataFrame(data)

    # Drop columns with complex objects (dicts, lists) that DataTable can't display
    cols_to_drop = []
    for col in df.columns:
        # Check if any cell in the column is a dict or list
        if any(isinstance(i, (dict, list)) for i in df[col]):
            cols_to_drop.append(col)
    df = df.drop(columns=cols_to_drop, errors="ignore")
    # Handle Categorical Enum Display
    enum_map = {
        "qc_status": QCStatus,
        "sex": SexKaryotype,
        "gender": SexKaryotype,
        "reported_sex": SexKaryotype,
        "predicted_sex": SexKaryotype,
        "original_pedigree_sex": SexKaryotype,
        "basic_statistics": QCStatus,
        "per_base_sequence_quality": QCStatus,
        "per_tile_sequence_quality": QCStatus,
        "per_sequence_quality_scores": QCStatus,
        "per_base_sequence_content": QCStatus,
        "per_sequence_gc_content": QCStatus,
        "per_base_n_content": QCStatus,
        "sequence_length_distribution": QCStatus,
        "sequence_duplication_levels": QCStatus,
        "overrepresented_sequences": QCStatus,
        "adapter_content": QCStatus,
    }
    for col, enum_class in enum_map.items():
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: str(enum_class(x)) if pd.notna(x) else "N/A"
            )

    # Move sample_name to the front and preserve model-defined order for the rest
    df = df.drop(columns=["id", "sample_id", "run_id"], errors="ignore")

    # Get the intended column order from the model definition
    model_field_order = list(tool_model.model_fields.keys())

    ordered_cols = []
    if "sample_name" in df.columns:
        ordered_cols.append("sample_name")
    # Add model fields that are present in the DataFrame, in their defined order
    for field in model_field_order:
        if field in df.columns and field not in ordered_cols:
            ordered_cols.append(field)
    ordered_cols.extend([col for col in df.columns if col not in ordered_cols])
    df = df[ordered_cols]

    return create_datatable(
        "metric-details-table",
        df.to_dict("records"),
        [{"name": i.replace("_", " ").title(), "id": i} for i in df.columns],
    )