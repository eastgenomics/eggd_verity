# Verity: An Interactive MultiQC Audit Tool

Verity is a comprehensive Quality Control (QC) audit and monitoring dashboard designed to visualise MultiQC metrics from bioinformatics pipelines. It provides an interactive interface to track trends over time, correlate different QC metrics, and explore data from DNAnexus projects.

Verity also enables bioinformaticians and lab scientists to monitor assay performance, identify outliers, and ensure data integrity across sequencing runs.

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
- **`queries/`**: Dedicated submodule for database interactions. Contains pure functions that accept parameters and return filtered DataFrames.
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

### Database Configuration

Verity supports SQLite (default) and PostgreSQL. The app, ETL pipeline,
manager scripts and Alembic all read the same settings (see `data/database.py`):

| Variable | Purpose |
| --- | --- |
| `VERITY_DATABASE_URL` | Full SQLAlchemy URL. Takes precedence when set. |
| `VERITY_DB_PATH` | Path to the SQLite file, used when no URL is set. Relative paths resolve from the project root. Default: `data/verity_db.sqlite3`. |

```bash
# SQLite (default, nothing to set), or a different file:
VERITY_DB_PATH=/path/to/verity_db.sqlite3

# PostgreSQL (postgres:// and postgresql:// use the bundled psycopg driver):
VERITY_DATABASE_URL=postgresql://user:password@host:5432/verity
```

Only `sqlite` and `postgresql` URLs are accepted. URL-encode special
characters in passwords (e.g. `@` as `%40`). Create or upgrade the schema on
a new database with `alembic upgrade head`.

## Testing

Verity includes a comprehensive test suite using `pytest` to ensure data integrity and application stability.

For instructions on setting up and running the tests, please refer to the Tests Documentation.

## Building a Docker Image

The image contains only code. The database is **not** baked in (it is excluded
by `.dockerignore`), so a database update never requires a new image. Neither
is `.env`: pass settings at runtime with `-e` or `--env-file`.

From the project root:

```bash
podman build -t docker.io/library/eggd_verity:latest .
```

## Saving the Image to a Compressed Archive

```bash
podman save --format docker-archive docker.io/library/eggd_verity:latest | gzip > verity_docker_image.tar.gz
```

## Packaging the SQLite Database

Compress the database separately from the image. Make sure the ETL pipeline is
not writing to it while you do this.

```bash
tar -czf verity_db.tar.gz -C data verity_db.sqlite3
```

The archive must contain `verity_db.sqlite3` at its top level, which is where
the container expects it (`/db/verity_db.sqlite3`).

## Uploading to DNAnexus

```bash
dx select proj-xx
dx upload verity_docker_image.tar.gz   # only when the code changed
dx upload verity_db.tar.gz             # whenever the data changed
```

## Running the Application

Inside the container the database is read from `/db/verity_db.sqlite3`
(`VERITY_DB_PATH`). Mount the directory holding it at `/db`. Mount it
read-write: SQLite writes journal files next to the database. If the file is
missing, requests fail with a clear "SQLite database not found" error instead
of serving an empty database.

### Docker (DNAnexus HTTP app or any Linux host)

Run this from the directory containing `verity_docker_image.tar.gz` and
`verity_db.tar.gz` (e.g. after `dx download`). It needs only `bash`, `tar` and
`docker`. Settings are passed through from the calling environment: export
`VERITY_SECRET_KEY` and, if auth is enabled, `VERITY_USERNAME` and `VERITY_PASSWORD`.

```bash
#!/usr/bin/env bash
set -euo pipefail

IMAGE_ARCHIVE="verity_docker_image.tar.gz"
DB_ARCHIVE="verity_db.tar.gz"
DB_DIR="$PWD/verity_db"

docker load -i "$IMAGE_ARCHIVE"

mkdir -p "$DB_DIR"
tar -xzf "$DB_ARCHIVE" -C "$DB_DIR"
if [ ! -f "$DB_DIR/verity_db.sqlite3" ]; then
    echo "verity_db.sqlite3 not found in $DB_ARCHIVE" >&2
    exit 1
fi

docker rm -f verity-container >/dev/null 2>&1 || true
docker run -d \
    --name verity-container \
    --restart unless-stopped \
    -p 8050:8050 \
    -v "$DB_DIR:/db" \
    -e VERITY_SECRET_KEY \
    -e VERITY_AUTH_ENABLED \
    -e VERITY_USERNAME \
    -e VERITY_PASSWORD \
    eggd_verity:latest
```

- `-v "$DB_DIR:/db"` mounts the extracted database into the container.
- `-e NAME` (without a value) copies that variable from the calling environment.
  Unset variables are skipped. Use `--env-file verity.env` instead if you prefer a file.

The application will now be accessible at `http://<server-ip>:8050`.

### Podman (local development)

```bash
podman run -d --name verity-container -p 8050:8050 \
    --env-file .env \
    -v "$PWD/data:/db:z" \
    docker.io/library/eggd_verity:latest
```

The `:z` suffix relabels the mount for SELinux (Fedora/RHEL). Without it the
container gets "permission denied". Docker on Ubuntu does not need it.

### Using PostgreSQL instead of SQLite

No volume is needed. Point the container at the server and create the schema once:

```bash
docker run --rm -e VERITY_DATABASE_URL eggd_verity:latest alembic upgrade head
docker run -d --name verity-container -p 8050:8050 \
    -e VERITY_DATABASE_URL -e VERITY_SECRET_KEY \
    eggd_verity:latest
```

## Managing the Container
Replace `docker` with `podman` if using podman

- **To view logs**: `docker logs verity-container`
- **To stop the container**: `docker stop verity-container`
- **To remove the container**: `docker rm verity-container`

## TODO

- **Revisit how per-FASTQ metrics are handled.** Tools marked `per_fastq` (FastQC,
  Picard base content) store one row per FASTQ file (lane and read pair), so each
  sample has several points in Trends and Raincloud. The hover box shows the sample
  count with the number of values, and an info note explains it. Still to decide:
  - Whether to bring back per-sample read totals. `Fastqc.total_unique_reads` and
    `total_duplicate_reads` were removed because they were misleading: they summed
    per-file estimates (FastQC's duplication level is based on the first 100,000
    reads of each file, and R1 and R2 are counted separately), then copied the total
    onto every file's row, so box mode's notch counted every copy. Picard or Samtools
    duplicate metrics may be the better source.
  - Whether plots should offer an aggregate per sample (mean or sum over files),
    or a lane or read pair filter.
