# Verity: Interactive MultiQC Audit Tool

Verity is a comprehensive Quality Control (QC) audit and monitoring dashboard designed to visualise MultiQC metrics from bioinformatics pipelines. It provides an interactive interface to track trends over time, correlate different QC metrics, and explore data from DNAnexus projects.

By aggregating data from MultiQC JSON reports, Verity enables bioinformaticians and lab scientists to monitor assay performance, identify outliers, and ensure data integrity across sequencing runs.

## Project Structure

The codebase is organised into two main modules: `app` for the frontend dashboard and `data` for backend data handling.

### `app/`
Contains the source code for the Dash web application.
- **`pages/`**: Defines the layout and callbacks for individual dashboard pages:
  - **Home**: High-level summary statistics and distribution charts.
  - **Trends**: Longitudinal tracking of QC metrics over time.
  - **Correlation**: Scatter plots to analyse relationships between two metrics.
  - **Raincloud Plot**: Detailed distribution analysis (Violin + Box + Strip plots) for specific metrics.
  - **Explore**: Tabular view of raw metric data for specific runs.
- **`components/`**: Reusable UI components (e.g. layout wrappers, filter controls).
- **`db.py`**: Database session management for the app.

### `data/`
Handles data ingestion, storage, and retrieval. This module is designed to be independent of the UI.
- **`models/`**: Database schema definitions using **SQLModel**. Each bioinformatics tool (e.g. Picard, Samtools) has its own model.
- **`queries/`**: Dedicated submodule for database interactions. Contains pure functions that accept parameters and return filtered DataFrames or results.
- **`plots/`**: Dedicated submodule for generating **Plotly** figures. Contains pure functions that take DataFrames and styling options to return graph objects.
- **`utils/`**: Helper functions for data formatting and model introspection.
- **`pipeline.py`**: The ETL (Extract, Transform, Load) script that interfaces with DNAnexus.

## Getting Started

1.  **Install Dependencies**: Ensure you have the required Python packages installed (see `requirements.txt`).
2.  **Database Setup**: Initialize the SQLite database using Alembic (see `data/README.md`).
3.  **Run ETL**: Populate the database with data from DNAnexus (see `data/README.md`).
4.  **Launch App**: Start the Dash server.
    ```bash
    python -m app.main
    ```

For detailed instructions on managing the database and running the data pipeline, refer to the **Data Module Documentation**.

## Testing

Verity includes a comprehensive test suite using `pytest` to ensure data integrity and application stability.

For instructions on setting up and running the tests, please refer to the Tests Documentation.
