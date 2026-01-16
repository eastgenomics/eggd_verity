# Verity Data Pipeline

This directory contains the core logic for the Verity backend, including the ETL pipeline, data models, query logic, and plotting functions.

## Database Migrations with Alembic

This project uses [Alembic](https://alembic.sqlalchemy.org/) to manage database schema migrations. This allows the database schema to evolve over time as data models change, without losing data.

### Initial Setup

Before running the pipeline for the first time, you must initialize the database with Alembic.

1.  **Generate the initial migration script:**
    This command will inspect models and create the first revision script to create all tables.

    ```bash
    alembic revision --autogenerate -m "Initial migration"
    ```

2.  **Apply the migration:**
    This command applies the revision script to the database, creating all the tables.

    ```bash
    alembic upgrade head
    ```
 
The database file (`verity_db.sqlite3`) will be created, and you can now run the ETL pipeline.

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

## Running the ETL Pipeline

The ETL (Extract, Transform, Load) pipeline scans DNAnexus for MultiQC JSON reports, processes them, and loads the metrics into the local SQLite database.

### First Run & Archival Handling

When running the pipeline for the first time (or on new projects), it scans for relevant files. **If any required reports are found to be archived on DNAnexus, the pipeline will automatically request that they be unarchived and then exit.**

You will need to wait for the unarchival process to complete (times vary by cloud provider) and then **rerun the pipeline**. On the subsequent run, the files will be accessible, and data ingestion will proceed.

### Execution & Deployment

In a deployment environment, the pipeline is typically scheduled using `cron` or a `systemd` timer to run periodically (e.g., nightly) to keep the dashboard up to date. However, it can be run manually from the command line for development, testing, or ad-hoc updates.

### Command Line Options

Run the pipeline using the module syntax:

```bash
python -m data.pipeline [OPTIONS]
```

**Examples:**

- **Run on specific projects:**  
  `python -m data.pipeline --project_ids='["project-xxxx", "project-yyyy"]'`  
  Useful for testing specific datasets or updating a single run.

- **Run on recent projects:**  
  `python -m data.pipeline --created_after="-30d"`  
  Scans only projects created in the last 30 days. This is the recommended flag for daily cron jobs to reduce API overhead.

- **Run on a random sample:**  
  `python -m data.pipeline --sample_size=10`  
  Processes a random subset of projects. Useful for quick testing during development.

- **View help:**  
  `python -m data.pipeline --help`