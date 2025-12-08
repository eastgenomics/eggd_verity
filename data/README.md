# Verity Data Pipeline

This directory contains the core logic for the Verity ETL pipeline, including data models, database configuration, and the main pipeline script.

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

Once the database is initialized and up-to-date, you can run the main ETL pipeline as before. The pipeline will now use the existing database managed by Alembic.


**Examples:**

- **To run on a specific list of projects:**
```bash
python -m data.pipeline project-xxx project-xyz
```