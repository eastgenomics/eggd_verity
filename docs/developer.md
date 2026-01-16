# Verity Developer Guide

Welcome to the Verity developer documentation. This guide provides technical details for contributors looking to understand, extend, or maintain the Verity codebase.

## Tech Stack

Verity is built using a modern Python stack designed for type safety, performance, and rapid development.

-   **Backend / Data Layer**:
    -   **[SQLModel](https://sqlmodel.tiangolo.com/)**: Combines SQLAlchemy and Pydantic for defining database models and interacting with the database.
    -   **[SQLAlchemy](https://www.sqlalchemy.org/)**: The underlying ORM handling database sessions and core SQL generation.
    -   **[Pydantic](https://docs.pydantic.dev/)**: Handles data validation and settings management.
    -   **[Alembic](https://alembic.sqlalchemy.org/)**: Manages database schema migrations.
    -   **SQLite**: The default relational database engine (serverless, file-based).

-   **Frontend / Dashboard**:
    -   **[Dash](https://dash.plotly.com/)**: A Python framework for building analytical web applications.
    -   **[Plotly](https://plotly.com/python/)**: The graphing library used for interactive charts.
    -   **[Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/)**: Provides Bootstrap styling and components for Dash.

-   **ETL & Utilities**:
    -   **[Pandas](https://pandas.pydata.org/)**: Used extensively for data manipulation and transformation during the ETL process.
    -   **[dxpy](https://github.com/dnanexus/dx-toolkit)**: The Python SDK for interacting with the DNAnexus platform.

---

## Data Architecture

### Database Choice
Verity currently uses **SQLite** (`verity_db.sqlite3`) for simplicity and ease of deployment. Since the application is read-heavy (dashboard) with periodic batch writes (ETL), SQLite performs exceptionally well.

**Changing the Database**:
Because Verity uses SQLModel (and thus SQLAlchemy), switching to PostgreSQL or MySQL is straightforward.
1.  Update the `DATABASE_URI` in `app/db.py` and `data/db_init.py`.
2.  Install the appropriate driver (e.g. `psycopg2`).
3.  Run Alembic migrations to initialize the schema on the new server.

### Data Models (`data/models/`)

The core of the application is the `BaseMetrics` class in `data/models/reports.py`.

#### `BaseMetrics`
This abstract base class provides standard functionality for all metric tables. **Crucially, any new tool added to Verity MUST inherit from `BaseMetrics`**. Failure to do so will break the dynamic model discovery used by the ETL pipeline and the UI.

**Key Class Methods to Override:**

-   `custom_transform(cls, df: pd.DataFrame) -> pd.DataFrame`:
    -   **Purpose**: Hook to clean or reshape raw MultiQC data before validation.
    -   **When to override**: If column names need remapping, if the data is nested (JSON), or if specific rows need filtering.
    -   **Example**: `data/models/fastqc.py` calculates unique/duplicate reads from raw counts.

-   `clean_df(cls, df: pd.DataFrame) -> pd.DataFrame`:
    -   **Purpose**: Standardises column names (snake_case) and coerces data types.
    -   **When to override**: Rarely. The default implementation is usually sufficient.

**Class Properties:**
-   `multiqc_section_names`: A list of strings matching the keys in the MultiQC JSON output. This maps the JSON data to the SQLModel.
-   `metric_level`: Set to `"sample"` (default) or `"run"`. Determines foreign key relationships.

### Modifying the Schema
1.  Modify the Python model in `data/models/`.
2.  Run `alembic revision --autogenerate -m "Description"`.
3.  Run `alembic upgrade head`.

---

## ETL Pipeline (`data/pipeline.py`)

The ETL pipeline is responsible for populating the database.

1.  **Extract**:
    -   Scans DNAnexus for `multiqc_data.json` files using `dxpy`.
    -   Handles archival states: if a file is archived, it requests unarchival and exits.

2.  **Transform**:
    -   Reads the JSON content.
    -   Iterates through sections defined in `model_map` (derived from `BaseMetrics` subclasses).
    -   Converts JSON sections to Pandas DataFrames.
    -   Calls `BaseMetrics.clean_df` and `custom_transform`.

3.  **Load**:
    -   Uses `bulk_create_from_df` to validate data against the Pydantic model and insert it into the database.
    -   Maintains referential integrity (Assay -> Run -> Sample -> Metrics).

### Adding New Data Sources
Currently, the pipeline is tightly coupled to DNAnexus via `data/utils/dnanexus.py`. To add a new source (e.g. S3, local files):
1.  Create a new utility module (e.g. `data/utils/s3_source.py`) that returns a DataFrame similar to `get_multiqc_reports`.
2.  Ensure the metadata extraction (Run folder, date, assay) matches the expected format.
3.  Update `data/pipeline.py` to call the new source function.

---

## Frontend Development (`app/`)

Verity uses a multi-page Dash application structure.

### Directory Structure
-   `app/pages/`: Individual pages. Each file registers itself via `dash.register_page`.
-   `app/components.py`: Reusable UI elements (cards, filter controls).
-   `app/utils.py`: Shared frontend logic (e.g. hover callbacks).

### Adding a New Page
1.  Create `app/pages/new_page.py`.
2.  Add `dash.register_page(__name__, path="/new", name="New Page")`.
3.  Define `layout` (can be a function or variable).
4.  Define callbacks using `@callback`.

### Adding a New Plot Type
1.  **Backend**: Create a pure plotting function in `data/plots/`.
    -   Input: Pandas DataFrame + styling arguments.
    -   Output: `plotly.graph_objects.Figure`.
    -   *Keep this logic separate from Dash to allow for easier testing.*
2.  **Frontend**: Import the function in your page and wire it up to a callback.

### Callbacks & State
-   Verity uses `dcc.Store` (session storage) for passing filters (like "Control Samples Only") between components without reloading the database.
-   Avoid global state. All state should be passed via callback Inputs/States.

---

## Testing

Tests are located in `tests/` and run via `pytest`.

-   **`tests/data/`**: Unit tests for models, queries, and plotting logic. Uses an in-memory SQLite database (`conftest.py`).
-   **`tests/app/`**: Integration tests for Dash callbacks. Mocks database sessions to test UI logic in isolation.

To run tests:
```bash
pytest
```

---

## Contribution Checklist

1.  [ ] Did you create a new `BaseMetrics` subclass for new tools?
2.  [ ] Did you generate an Alembic migration?
3.  [ ] Did you add unit tests for new queries or plots?
4.  [ ] Did you verify the ETL pipeline runs against the new schema?
```

```diff