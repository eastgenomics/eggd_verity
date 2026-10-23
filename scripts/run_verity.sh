#!/usr/bin/env bash
# Launch the eggd_verity HTTP applet in the verity dev project with the newest Docker image and database archive.

set -euo pipefail

# Project holding the eggd_verity applet, image and database archives
DEV_PROJECT="project-GjQJ6gQ4JKFyzkYgvFj7kvj6"
APPLET="/eggd_verity"
IMAGE_PATTERN="verity_docker_image*.tar.gz"
DATA_PATTERN="verity_db*.tar.gz"
IMAGE_ID=""
DATA_ID=""

usage() {
    cat <<USAGE
Usage: $(basename "$0") [-p PROJECT] [-i IMAGE_FILE_ID] [-d DATA_FILE_ID] [-- DX_RUN_ARGS...]

Runs the ${APPLET#/} applet with the newest image ($IMAGE_PATTERN) and database
archive ($DATA_PATTERN) in the project. Arguments after -- go to 'dx run'.

  -p PROJECT        DNAnexus project (default: $DEV_PROJECT)
  -i IMAGE_FILE_ID  Use this image instead of the newest one
  -d DATA_FILE_ID   Use this database archive instead of the newest one
  -h                Show this help
USAGE
}

while getopts "p:i:d:h" opt; do
    case "$opt" in
        p) DEV_PROJECT="$OPTARG" ;;
        i) IMAGE_ID="$OPTARG" ;;
        d) DATA_ID="$OPTARG" ;;
        h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
shift $((OPTIND - 1))

if [[ -z "$DEV_PROJECT" ]]; then
    echo "Set DEV_PROJECT in $0 or pass -p project-..." >&2
    exit 2
fi

dx whoami >/dev/null || { echo "Log in with 'dx login' first" >&2; exit 1; }
dx select "$DEV_PROJECT" >/dev/null

# Gets the ID of the newest closed file matching a name glob in given project.
latest_file() {
    dx find data --class file --state closed --path "$DEV_PROJECT:/" \
        --name "$1" --name-mode glob --verbose --json \
        | jq -r 'max_by(.describe.created) | .id // empty'
}

IMAGE_ID="${IMAGE_ID:-$(latest_file "$IMAGE_PATTERN")}"
DATA_ID="${DATA_ID:-$(latest_file "$DATA_PATTERN")}"
[[ -n "$IMAGE_ID" ]] || { echo "No $IMAGE_PATTERN found in $DEV_PROJECT" >&2; exit 1; }
[[ -n "$DATA_ID" ]] || { echo "No $DATA_PATTERN found in $DEV_PROJECT" >&2; exit 1; }

describe() { dx describe "$1" --json | jq -r '"\(.name) (\(.id), created \(.created / 1000 | todate))"'; }
echo "Image:    $(describe "$IMAGE_ID")"
echo "Database: $(describe "$DATA_ID")"

JOB_ID="$(dx run "$DEV_PROJECT:$APPLET" \
    -iimage="$IMAGE_ID" -idata="$DATA_ID" \
    --project "$DEV_PROJECT" --yes --brief "$@")"
echo "Started $JOB_ID"
echo "Watch it with: dx watch $JOB_ID"
