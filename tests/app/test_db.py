import sqlite3

import pytest
from sqlalchemy import text

from app import db
from data import database


@pytest.fixture
def env(monkeypatch):
    values: dict[str, str] = {}
    monkeypatch.setattr(
        database, "config", lambda key, default=None: values.get(key, default)
    )
    database._cached_engine.cache_clear()
    yield values
    database._cached_engine.cache_clear()


def test_get_session_uses_configured_sqlite(env, tmp_path):
    db_file = tmp_path / "verity.sqlite3"
    with sqlite3.connect(db_file) as conn:
        conn.execute("create table t (x int)")
        conn.execute("insert into t values (7)")
    env["VERITY_DB_PATH"] = str(db_file)

    with db.get_session() as session:
        assert session.exec(text("select x from t")).scalar() == 7


def test_get_session_missing_db_fails_without_creating_file(env, tmp_path):
    missing = tmp_path / "not_mounted" / "verity.sqlite3"
    env["VERITY_DB_PATH"] = str(missing)

    with pytest.raises(FileNotFoundError, match="mount"):
        db.get_session()
    assert not missing.exists()
    assert not missing.parent.exists()


def test_get_session_postgres_does_not_connect_eagerly(env):
    pytest.importorskip("psycopg")
    env["VERITY_DATABASE_URL"] = "postgres://u:p@127.0.0.1:1/verity"

    session = db.get_session()
    assert session.get_bind().dialect.name == "postgresql"
    session.close()
