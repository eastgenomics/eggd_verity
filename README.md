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

### Authentication

Basic Auth is enabled by default. Configure it through environment variables:

```bash
VERITY_AUTH_ENABLED=true
VERITY_USERNAME=your-username
VERITY_PASSWORD=your-password
VERITY_SECRET_KEY=your-secret-key
```

To disable Basic Auth for local development or an environment protected by a
trusted firewall or identity-aware reverse proxy, explicitly set:

```bash
VERITY_AUTH_ENABLED=false
```

The flag accepts `true`, `1`, `yes`, `on`, `false`, `0`, `no`, and `off`.
Invalid values fail during startup. Username and password are required when
authentication is enabled and may be omitted when it is explicitly disabled.
Use HTTPS in deployed environments and inject credentials through the environment or a secret manager.

For detailed instructions on managing the database and running the data pipeline, refer to the **Data Module Documentation**.

## Testing

Verity includes a comprehensive test suite using `pytest` to ensure data integrity and application stability.

For instructions on setting up and running the tests, please refer to the Tests Documentation.

## Building a Docker Image

To build the Docker image for the verity, navigate to the project's root directory (the one containing the `Dockerfile`) and run the following command:

```bash
podman build -t docker.io/library/eggd_verity:latest .
```

This command will:
- Use the `Dockerfile` to build a new image.
- Tag the image with the name `eggd_verity`.

## Saving the Image to a Compressed Archive

Once the image is built, you can save it to a compressed tarball (`.tar.gz`) for easy distribution.

```bash
podman save --format docker-archive docker.io/library/eggd_verity:latest | gzip > verity_docker_image.tar.gz
```

You can now transfer the `verity_docker_image.tar.gz` file to the deployment server. Or Upload to DNAnexus

```
dx select proj-xx

dx upload verity_docker_image.tar.gz
```

## Loading and Running the Application from the Archive

On the deployment server, follow these steps:

1.  **Load the Docker image** from the tarball:

    ```bash
    docker load < verity_docker_image.tar.gz
    ```

2.  **Run the application** in a new container:

    ```bash
    docker run -d -p 8050:8050 --name verity-container eggd_verity
    ```
    - `-d` runs the container in detached mode (in the background).
    - `-p 8050:8050` maps port 8050 on the host to port 8050 in the container.
    - `--name verity-container` gives the running container a memorable name.

The application will now be accessible at `http://<server-ip>:8050`.

## Managing the Container

- **To view logs**: `docker logs verity-container`
- **To stop the container**: `docker stop verity-container`
- **To remove the container**: `docker rm verity-container`

