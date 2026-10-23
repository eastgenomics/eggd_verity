#!/usr/bin/env bash
# Refresh the Verity SQLite database from DNAnexus and upload an archive of to the given dev project
# Run from anywhere with the Verity virtualenv active and the dx CLI logged in.
set -euo pipefail

# Project holding the eggd_verity applet, image and database archives
DEV_PROJECT="project-GjQJ6gQ4JKFyzkYgvFj7kvj6"
CREATED_AFTER="-2w"
FOLDER="/"
PYTHON="${PYTHON:-python}"

usage() {
    cat <<USAGE
Usage: $(basename "$0") [-p PROJECT] [-a CREATED_AFTER] [-f FOLDER]

Runs the ETL pipeline, archives the SQLite database and uploads the archive
to DNAnexus.

  -p PROJECT        DNAnexus project to upload to (default: $DEV_PROJECT)
  -a CREATED_AFTER  Passed to the pipeline as --created_after (default: $CREATED_AFTER)
  -f FOLDER         Folder in the project to upload to (default: $FOLDER)
  -h                Show this help
USAGE
}

while getopts "p:a:f:h" opt; do
    case "$opt" in
        p) DEV_PROJECT="$OPTARG" ;;
        a) CREATED_AFTER="$OPTARG" ;;
        f) FOLDER="$OPTARG" ;;
        h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

if [[ -z "$DEV_PROJECT" ]]; then
    echo "Set DEV_PROJECT in $0 or pass -p project-..." >&2
    exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${VERITY_DB_PATH:-$REPO_ROOT/data/verity_db.sqlite3}"
case "$DB_PATH" in /*) ;; *) DB_PATH="$REPO_ROOT/$DB_PATH" ;; esac

dx whoami >/dev/null || { echo "Log in with 'dx login' first" >&2; exit 1; }
dx select "$DEV_PROJECT" >/dev/null

echo "Running the ETL pipeline (--created_after=$CREATED_AFTER)..."
(cd "$REPO_ROOT" && "$PYTHON" -m data.pipeline --created_after="$CREATED_AFTER")

if [[ ! -f "$DB_PATH" ]]; then
    echo "Database not found at $DB_PATH" >&2
    exit 1
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# The date in the name is for people; run_verity.sh picks the newest by creation time
ARCHIVE="$WORK_DIR/verity_db_$(date +%Y%m%d_%H%M).tar.gz"
# The applet expects verity_db.sqlite3 at the top level of the archive
tar -czf "$ARCHIVE" --transform "s|^$(basename "$DB_PATH")\$|verity_db.sqlite3|" \
    -C "$(dirname "$DB_PATH")" "$(basename "$DB_PATH")"

echo "Uploading $(basename "$ARCHIVE") to $DEV_PROJECT:$FOLDER..."
FILE_ID="$(dx upload "$ARCHIVE" --path "$DEV_PROJECT:${FOLDER%/}/" --brief --wait)"
echo "Uploaded database archive: $FILE_ID"
