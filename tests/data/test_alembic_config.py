"""Alembic must use the same database settings as the app and pipeline."""

import os
import sqlite3
import subprocess
import sys

import pytest

from data.database import PROJECT_ROOT


def run_alembic(*args, **env_overrides):
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("VERITY_DATABASE_URL", "VERITY_DB_PATH")
    }
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_upgrade_head_on_new_sqlite_via_db_path(tmp_path):
    db_file = tmp_path / "nested" / "verity.sqlite3"
    db_file.parent.mkdir()
    result = run_alembic("upgrade", "head", VERITY_DB_PATH=str(db_file))
    assert result.returncode == 0, result.stderr

    tables = {
        row[0]
        for row in sqlite3.connect(db_file).execute(
            "select name from sqlite_master where type='table'"
        )
    }
    assert {"alembic_version", "assay", "run", "sample"} <= tables


def test_database_url_overrides_db_path(tmp_path):
    used = tmp_path / "used.sqlite3"
    ignored = tmp_path / "ignored.sqlite3"
    result = run_alembic(
        "current",
        VERITY_DB_PATH=str(ignored),
        VERITY_DATABASE_URL=f"sqlite:///{used}",
    )
    assert result.returncode == 0, result.stderr
    assert used.exists()
    assert not ignored.exists()


def test_offline_sql_for_postgres():
    pytest.importorskip("psycopg")
    result = run_alembic(
        "upgrade",
        "head",
        "--sql",
        VERITY_DATABASE_URL="postgresql://u:p@localhost/verity",
    )
    assert result.returncode == 0, result.stderr
    assert "CREATE TABLE assay" in result.stdout


def test_unsupported_backend_fails():
    result = run_alembic("current", VERITY_DATABASE_URL="mysql://u:p@h/db")
    assert result.returncode != 0
    assert "Unsupported database backend" in result.stderr
