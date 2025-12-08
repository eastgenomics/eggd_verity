# eggd_verity
An Interactive MultiQC Audit Tool

## Data Pipeline

The project includes a data pipeline to find MultiQC reports in DNAnexus, process them, and load the data into a local SQLite database.

### Usage

The pipeline is run from the command line. You can view all available options by running the script with the `--help` flag:
 
```bash
python -m data.pipeline -- --help
```

**Examples:**

- **To run on a specific list of projects:**
  ```bash
  python -m data.pipeline --project_ids='["project-xxxx", "project-yyyy"]'
  ```
- **To run on projects created in the last 30 days:**
  ```bash
  python -m data.pipeline --created_after="-30d"
  ```
- **To run on a random sample of 10 projects:**
  ```bash
  python -m data.pipeline --sample_size=10
  ```
