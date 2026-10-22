"""The image must not contain the database or secrets; the DB is mounted at runtime."""

import re

import pytest

from data.database import PROJECT_ROOT


def _pattern_to_regex(pattern: str) -> re.Pattern:
    pattern = pattern.strip().lstrip("/").rstrip("/")
    regex = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            regex += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            regex += ".*"
            i += 2
        elif pattern[i] == "*":
            regex += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            regex += "[^/]"
            i += 1
        else:
            regex += re.escape(pattern[i])
            i += 1
    return re.compile(f"^{regex}$")


def _ignore_patterns() -> list[re.Pattern]:
    lines = (PROJECT_ROOT / ".dockerignore").read_text().splitlines()
    patterns = [line for line in lines if line.strip() and not line.startswith("#")]
    assert not any(p.startswith("!") for p in patterns), "negations not supported here"
    return [_pattern_to_regex(p) for p in patterns]


def is_ignored(path: str) -> bool:
    """A path is excluded if it, or any parent directory, matches a pattern."""
    parts = path.split("/")
    candidates = ["/".join(parts[: i + 1]) for i in range(len(parts))]
    return any(p.match(c) for p in _ignore_patterns() for c in candidates)


@pytest.mark.parametrize(
    "path",
    [
        "data/verity_db.sqlite3",
        "data/verity_db.sqlite3.backup",
        "data/verity_db.sqlite3-journal",
        "data/verity_db.sqlite3-wal",
        "verity_db.sqlite3",
        "db/verity_db.sqlite3",
        ".env",
        "app/.env",
        ".env.local",
        "verity_docker_image.tar.gz",
        "verity_db.tar.gz",
        "logs/app.log",
        "data/sex_check_result.xlsx",
        "data/samples.txt",
        ".venv/bin/python",
        "app/__pycache__/db.cpython-312.pyc",
        ".git/HEAD",
    ],
)
def test_excluded_from_build_context(path):
    assert is_ignored(path)


@pytest.mark.parametrize(
    "path",
    [
        "app/main.py",
        "app/db.py",
        "data/database.py",
        "data/config.py",
        "data/models/reports.py",
        "alembic/env.py",
        "alembic/versions/f67693ee953b_initial_migration.py",
        "alembic.ini",
        "requirements.txt",
        "Dockerfile",
    ],
)
def test_code_kept_in_build_context(path):
    assert not is_ignored(path)


def test_dockerfile_points_db_at_mount():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text()
    assert "ENV VERITY_DB_PATH=/db/verity_db.sqlite3" in dockerfile
    assert not re.search(r"^ENV\s+VERITY_DATABASE_URL", dockerfile, re.M)
