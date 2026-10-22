import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from data import database
from data.database import (
    DEFAULT_DATABASE_PATH,
    PROJECT_ROOT,
    build_engine,
    ensure_database_available,
    get_engine,
    normalise_database_url,
    redact_database_url,
    resolve_database_url,
    resolve_sqlite_path,
    sqlite_file_path,
)


@pytest.fixture
def env(monkeypatch):
    """Isolate settings from the real environment and any local .env file."""
    values: dict[str, str] = {}
    monkeypatch.setattr(
        database, "config", lambda key, default=None: values.get(key, default)
    )
    database._cached_engine.cache_clear()
    yield values
    database._cached_engine.cache_clear()


# --- URL resolution ---------------------------------------------------------


def test_defaults_to_sqlite_in_data_dir(env):
    assert resolve_database_url() == f"sqlite:///{DEFAULT_DATABASE_PATH}"
    assert DEFAULT_DATABASE_PATH == PROJECT_ROOT / "data" / "verity_db.sqlite3"


def test_db_path_absolute(env, tmp_path):
    env["VERITY_DB_PATH"] = str(tmp_path / "verity.sqlite3")
    assert resolve_database_url() == f"sqlite:///{tmp_path / 'verity.sqlite3'}"


def test_db_path_relative_resolves_against_project_root_not_cwd(env, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env["VERITY_DB_PATH"] = "data/other.sqlite3"
    assert resolve_database_url() == f"sqlite:///{PROJECT_ROOT / 'data' / 'other.sqlite3'}"


def test_db_path_expands_home(env, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    env["VERITY_DB_PATH"] = "~/db/verity.sqlite3"
    assert resolve_database_url() == f"sqlite:///{tmp_path / 'db' / 'verity.sqlite3'}"


def test_db_path_with_spaces(env, tmp_path):
    path = tmp_path / "my dir" / "verity db.sqlite3"
    env["VERITY_DB_PATH"] = str(path)
    assert sqlite_file_path(resolve_database_url()) == path


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_settings_fall_back_to_default(env, blank):
    env["VERITY_DATABASE_URL"] = blank
    env["VERITY_DB_PATH"] = blank
    assert resolve_database_url() == f"sqlite:///{DEFAULT_DATABASE_PATH}"


def test_database_url_takes_precedence_over_db_path(env, tmp_path):
    env["VERITY_DB_PATH"] = str(tmp_path / "ignored.sqlite3")
    env["VERITY_DATABASE_URL"] = "postgresql+psycopg://u:p@db:5432/verity"
    assert resolve_database_url() == "postgresql+psycopg://u:p@db:5432/verity"


def test_database_url_is_stripped(env):
    env["VERITY_DATABASE_URL"] = "  sqlite:////db/verity.sqlite3  \n"
    assert resolve_database_url() == "sqlite:////db/verity.sqlite3"


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql://u:p@h:5433/db", "postgresql+psycopg://u:p@h:5433/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg2://u:p@h/db", "postgresql+psycopg2://u:p@h/db"),
        ("postgresql://u:p@h/db?sslmode=require", "postgresql+psycopg://u:p@h/db?sslmode=require"),
        ("sqlite:///relative.sqlite3", "sqlite:///relative.sqlite3"),
        ("sqlite://", "sqlite://"),
        ("sqlite:///:memory:", "sqlite:///:memory:"),
    ],
)
def test_normalise_database_url(given, expected):
    assert normalise_database_url(given) == expected


def test_password_special_characters_survive_normalisation():
    url = "postgresql://user:p%40ss%3Aw%2Frd%25@host/db"
    normalised = normalise_database_url(url)
    assert make_url(normalised).password == "p@ss:w/rd%"


@pytest.mark.parametrize(
    "url", ["mysql://u:p@h/db", "mssql+pyodbc://h/db", "oracle://h/db"]
)
def test_unsupported_backend_rejected(url):
    with pytest.raises(ValueError, match="Unsupported database backend"):
        normalise_database_url(url)


@pytest.mark.parametrize("url", ["not a url", "/data/verity_db.sqlite3", "://nope"])
def test_invalid_url_rejected(url):
    with pytest.raises(ValueError, match="VERITY_DATABASE_URL"):
        normalise_database_url(url)


def test_invalid_url_from_env_rejected(env):
    env["VERITY_DATABASE_URL"] = "mysql://u:p@h/db"
    with pytest.raises(ValueError):
        resolve_database_url()


# --- helpers ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("sqlite:////db/verity.sqlite3", Path("/db/verity.sqlite3")),
        ("sqlite://", None),
        ("sqlite:///:memory:", None),
        ("postgresql+psycopg://u:p@h/db", None),
    ],
)
def test_sqlite_file_path(url, expected):
    assert sqlite_file_path(url) == expected


def test_resolve_sqlite_path_absolute_unchanged(tmp_path):
    assert resolve_sqlite_path(tmp_path / "x.sqlite3") == tmp_path / "x.sqlite3"


def test_redact_database_url_hides_password():
    redacted = redact_database_url("postgresql+psycopg://user:s3cret@host/db")
    assert "s3cret" not in redacted
    assert "user" in redacted and "host" in redacted


def test_redact_database_url_without_password():
    assert redact_database_url("sqlite:////db/v.sqlite3") == "sqlite:////db/v.sqlite3"


# --- engines ----------------------------------------------------------------


def test_sqlite_engine_sets_timeout_not_pre_ping(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(database, "create_engine", lambda url, **kw: calls.append(kw))
    build_engine(f"sqlite:///{tmp_path / 'v.sqlite3'}")
    assert calls == [{"connect_args": {"timeout": database.SQLITE_TIMEOUT_SECONDS}}]


def test_sqlite_engine_merges_custom_connect_args(tmp_path):
    engine = build_engine(
        f"sqlite:///{tmp_path / 'v.sqlite3'}",
        connect_args={"check_same_thread": False},
    )
    with engine.connect() as conn:
        assert conn.execute(text("select 1")).scalar() == 1


def test_postgres_engine_uses_psycopg_and_pre_ping():
    pytest.importorskip("psycopg")
    engine = build_engine(normalise_database_url("postgresql://u:p@localhost/db"))
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg"
    assert engine.pool._pre_ping is True


def test_get_engine_is_cached_per_url(env, tmp_path):
    env["VERITY_DB_PATH"] = str(tmp_path / "a.sqlite3")
    first = get_engine()
    assert get_engine() is first

    env["VERITY_DB_PATH"] = str(tmp_path / "b.sqlite3")
    assert get_engine() is not first


def test_get_engine_reads_and_writes_configured_sqlite(env, tmp_path):
    db_file = tmp_path / "v.sqlite3"
    env["VERITY_DB_PATH"] = str(db_file)
    with get_engine().begin() as conn:
        conn.execute(text("create table t (x int)"))
        conn.execute(text("insert into t values (42)"))
    assert sqlite3.connect(db_file).execute("select x from t").fetchone() == (42,)


# --- availability check -----------------------------------------------------


def test_ensure_database_available_missing_file(tmp_path):
    missing = tmp_path / "missing.sqlite3"
    with pytest.raises(FileNotFoundError, match="VERITY_DB_PATH"):
        ensure_database_available(f"sqlite:///{missing}")
    assert not missing.exists()


def test_ensure_database_available_rejects_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        ensure_database_available(f"sqlite:///{tmp_path}")


def test_ensure_database_available_existing_file(tmp_path):
    db_file = tmp_path / "v.sqlite3"
    db_file.touch()
    ensure_database_available(f"sqlite:///{db_file}")


@pytest.mark.parametrize("url", ["sqlite://", "postgresql+psycopg://u:p@h/db"])
def test_ensure_database_available_skips_non_file_databases(url):
    ensure_database_available(url)
