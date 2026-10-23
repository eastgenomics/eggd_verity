# Verity Data Pipeline

This directory contains the core logic for the Verity backend, including the ETL pipeline, data models, query logic, and plotting functions.

## Database Migrations with Alembic

This project uses [Alembic](https://alembic.sqlalchemy.org/) to manage database schema migrations. This allows the database schema to evolve over time as data models change, without losing data.

### Initial Setup

The migrations start from a single baseline revision that creates every table. To build a new database, apply it:

```bash
alembic upgrade head
```

The database (by default `data/verity_db.sqlite3`; see *Database Configuration* in the main README to use another file or PostgreSQL) will be created, and you can now run the ETL pipeline.

### Future Schema Changes

Whenever a change is made to a `SQLModel` class in the `data/models/` directory (e.g. add a new column, create a new metric table), a new migration script must be generated.

1.  **Generate a new revision:**
    Alembic will detect the changes and generate a new script.

    ```bash
   alembic revision --autogenerate -m "A brief description of your changes"
    ```

2.  **Apply the new migration:**
    This will apply the changes to the existing database without deleting any data.

    ```bash
    alembic upgrade head
   ```

## Removing a duplicate MultiQC report

When a project has more than one MultiQC report holding the same samples (for example a rerun), the plot pages show a warning with the report file ids. Remove the unwanted report with:

```bash
python -m data.manager.remove_data_source file-XXXX                  # dry run, prints what would be deleted
python -m data.manager.remove_data_source file-XXXX --dry_run=False  # delete
```

This deletes the report's metric rows, then samples that no longer have any metrics, then the run if it has no reports left. The pipeline loads any live report that is not in the database, so a removed report comes back if its project is scanned again (for example while it is still inside the `created_after` window). Remove it after the project has left the window, or remove the unwamted file from the DNAnexus project.

## Running the ETL Pipeline

The ETL (Extract, Transform, Load) pipeline scans DNAnexus for MultiQC JSON reports, processes them, and loads the metrics into verity database.

### First Run & Archival Handling

When running the pipeline for the first time (or on new projects), it scans for relevant files. **If any required reports are found to be archived on DNAnexus, the pipeline will automatically request that they be unarchived and then exit.**

You will need to wait for the unarchival process to complete and then **rerun the pipeline**. On the subsequent run, the files will be accessible, and data ingestion will proceed.

### Execution & Deployment

In a deployment environment, the pipeline is typically scheduled using `cron` or a `systemd` timer to run periodically (e.g. every 6 hours) to keep the database up to date. However, it can be run manually from the command line for development, testing, or ad-hoc updates.

### Command Line Options

Run the pipeline using the module syntax:

```bash
python -m data.pipeline [OPTIONS]
```

**Examples:**

- **Run on specific projects:**  
  `python -m data.pipeline "project-xxxx" "project-yyyy"`
  Useful for testing specific datasets or updating a single run.

- **Run on recent projects:**  
  `python -m data.pipeline --created_after="-2w"`  
  Scans only projects created in the last 2 weeks. This is the recommended flag for daily cron jobs to reduce API overhead.
  Also accepts `d` eg `--created_after="-14d"`and `h` eg `--created_after="-48h"`  for days and hours respectively.

- **Run on a random sample:**  
  `python -m data.pipeline --sample_size=10`  
  Processes a random subset of projects. Useful for quick testing during development.

- **View help:**  
  `python -m data.pipeline --help`

### Updating Assay Status

The legacy status manager marks configured assay names as inactive. The
initial list is `CEN`, `FH`, `SNP`, `TSOE`, and `TWE`; it can be extended in
`data/manager/update_assay_status.py`. 

The command is a dry run by default:

```bash
python -m data.manager.update_assay_status
```

Apply the changes explicitly with:

```bash
python -m data.manager.update_assay_status --dry_run=False
```

The Dashboard excludes inactive assays by default. Its session-persistent
`Include legacy assays` switch includes them in the Dashboard summary table
and charts when enabled. Trends, Correlation, Explore Data, and Raincloud
Plot are not filtered by this setting.