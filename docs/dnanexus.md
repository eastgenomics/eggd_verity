# Running Verity on DNAnexus

Two scripts in `scripts/` automate the routine DNAnexus steps: refreshing the
database and launching the app.

These scripts are only for running Verity as a DNAnexus HTTP app. They assume:

- The `eggd_verity` applet is in the root of the dev project. It takes two file
  inputs: `image` (the Docker image archive) and `data` (the database archive).
- The Docker image archive (`verity_docker_image*.tar.gz`) has already been
  uploaded to the project. The image changes rarely, so this stays a manual step
  (see *Updating the image* below).
- The dx CLI is installed and logged in (`dx login`), and `jq` is installed.
- For the database script: the verity virtualenv is active and `.env` has a valid
  `DX_TOKEN` for the pipeline.

## Project

Both scripts default to the verity dev project set in `DEV_PROJECT` near the top of
each script. If the project changes, update it there:

```bash
DEV_PROJECT="project-GjQJ6gQ4JKFyzkYgvFj7kvj6"
```

You can also pass `-p project-xxx` on each run instead. The scripts call
`dx select` on the project themselves.

## Updating the database: `scripts/update_verity_db.sh`

```bash
scripts/update_verity_db.sh      # defaults: dev project, last 2 weeks
scripts/update_verity_db.sh -a "-30d"   # look further back
scripts/update_verity_db.sh -f /verity_db    # upload into a folder
```

This does the following:

1. Runs the ETL pipeline: `python -m data.pipeline --created_after=-2w`. The
   2-week default overlaps the usual 2-day schedule (but can be run as often as you want), so a missed run is caught up.
   Reports already in the database are skipped.
2. Archives the database as `verity_db_YYYYMMDD_HHMM.tar.gz`, with
   `verity_db.sqlite3` at the top level, as the applet expects.
3. Uploads the archive to the project and prints its file ID.

| Option | Default | Meaning |
|---|---|---|
| `-p PROJECT` | `DEV_PROJECT` | Project to upload to |
| `-a CREATED_AFTER` | `-2w` | Passed to the pipeline as `--created_after` |
| `-f FOLDER` | `/` | Folder in the project to upload to |

The database is read from `VERITY_DB_PATH` if that is set, otherwise from
`data/verity_db.sqlite3`. Set `PYTHON=/path/to/python` to use a different
interpreter.

If the pipeline finds archived MultiQC files on DNAnexus, it sends an
unarchival request and exits without loading them. The script still uploads the
database, so rerun it once the files are live.

## Launching the app: `scripts/run_verity.sh`

```bash
scripts/run_verity.sh   # newest image and database
scripts/run_verity.sh -d file-xxx   # a specific database archive
scripts/run_verity.sh -- --instance-type mem1_ssd1_v2_x4 # extra dx run arguments
```

The script finds the most recent `verity_docker_image*.tar.gz` and
`verity_db*.tar.gz` in the project, by creation time. It prints what it picked,
then runs:

```bash
dx run eggd_verity -iimage=<image file-id> -idata=<database file-id> --project project-xxx -y
```

It prints the job ID. Follow the job with `dx watch <job-id>`. <br>
Open the app under the Worker URL tab from the DNAnexus job monitor page once it is running.

| Option | Default | Meaning |
|---|---|---|
| `-p PROJECT` | `DEV_PROJECT` | Project with the applet and archives |
| `-i IMAGE_FILE_ID` | newest image | Use a specific image |
| `-d DATA_FILE_ID` | newest database archive | Use a specific database archive |
| `-- ARGS` | | Passed on to `dx run` |

## A typical cycle

```bash
scripts/update_verity_db.sh   # every 2 days
scripts/run_verity.sh
```

Terminate the previous app job if it is still running (`dx terminate <job-id>`).
Old database archives stay in the project, so remove them now and then.

## Updating the image

When the code changes, build and upload a new image by hand (see *Building a
Docker Image* in the main README):

```bash
podman build -t docker.io/library/eggd_verity:latest .
podman save --format docker-archive docker.io/library/eggd_verity:latest | gzip > verity_docker_image.tar.gz
dx upload verity_docker_image.tar.gz --path project-xxx:/
```

`run_verity.sh` automatically picks it up on its next run, because it is the newest image.
