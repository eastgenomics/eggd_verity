"""
Database configuration shared by the Dash app, ETL pipeline, manager scripts
and Alembic.

The database is selected with environment variables (or a `.env` file):

- ``VERITY_DATABASE_URL``: full SQLAlchemy URL, e.g.
  ``postgresql+psycopg://user:pass@host:5432/verity`` or
  ``sqlite:////db/verity_db.sqlite3``. Takes precedence when set.
- ``VERITY_DB_PATH``: path to a SQLite file, used when no URL is set.
  Relative paths are resolved against the project root. Defaults to
  ``data/verity_db.sqlite3``.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from decouple import config
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import ArgumentError
from sqlmodel import create_engine

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_DATABASE_FILE = "verity_db.sqlite3"
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / DEFAULT_DATABASE_FILE

SUPPORTED_BACKENDS = {"sqlite", "postgresql"}
POSTGRES_DRIVER = "psycopg"
SQLITE_TIMEOUT_SECONDS = 60


def resolve_sqlite_path(db_path: str | Path) -> Path:
    """Expand ``~`` and resolve a relative SQLite path against the project root."""
    path = Path(db_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def normalise_database_url(database_url: str) -> str:
    """
    Validate a database URL and fill in the default Postgres driver.

    ``postgres://`` and ``postgresql://`` URLs are rewritten to use psycopg
    (version 3), the driver installed in the image. An explicit driver,
    e.g. ``postgresql+psycopg2://``, is kept as given.

    Raises
    ------
    ValueError
        If the URL cannot be parsed or the backend is not supported.
    """
    url_str = database_url.strip()
    if url_str.startswith("postgres://"):
        url_str = "postgresql://" + url_str[len("postgres://"):]

    try:
        url = make_url(url_str)
    except ArgumentError as exc:
        raise ValueError(f"VERITY_DATABASE_URL is not a valid database URL: {exc}") from None

    if url.get_backend_name() not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"Unsupported database backend {url.get_backend_name()!r} in "
            f"VERITY_DATABASE_URL; supported: {', '.join(sorted(SUPPORTED_BACKENDS))}"
        )

    if url.get_backend_name() == "postgresql" and "+" not in url.drivername:
        url = url.set(drivername=f"postgresql+{POSTGRES_DRIVER}")

    return url.render_as_string(hide_password=False)


def resolve_database_url() -> str:
    """Return the database URL from ``VERITY_DATABASE_URL`` or ``VERITY_DB_PATH``."""
    database_url = config("VERITY_DATABASE_URL", default="").strip()
    if database_url:
        return normalise_database_url(database_url)

    db_path = config("VERITY_DB_PATH", default="").strip() or DEFAULT_DATABASE_PATH
    return f"sqlite:///{resolve_sqlite_path(db_path)}"


def sqlite_file_path(database_url: str) -> Path | None:
    """Return the file path of a SQLite URL, or None for in-memory/non-SQLite URLs."""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or url.database in (None, "", ":memory:"):
        return None
    return Path(url.database)


def redact_database_url(database_url: str) -> str:
    """Return the URL with any password masked, for logging."""
    return make_url(database_url).render_as_string(hide_password=True)


def build_engine(database_url: str, **kwargs: Any) -> Engine:
    """Create an engine with backend-appropriate defaults."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        connect_args = {"timeout": SQLITE_TIMEOUT_SECONDS, **kwargs.pop("connect_args", {})}
        kwargs["connect_args"] = connect_args
    else:
        kwargs.setdefault("pool_pre_ping", True)

    logger.debug(f"Creating database engine for {redact_database_url(database_url)}")
    return create_engine(url, **kwargs)


@lru_cache(maxsize=None)
def _cached_engine(database_url: str) -> Engine:
    return build_engine(database_url)


def get_engine(database_url: str | None = None) -> Engine:
    """Return a shared engine for the configured (or given) database URL."""
    return _cached_engine(database_url or resolve_database_url())


def ensure_database_available(database_url: str) -> None:
    """
    Fail fast with a clear message when a SQLite database file is missing.

    SQLite would otherwise silently create an empty file, e.g. when the
    database volume was not mounted into the container.
    """
    path = sqlite_file_path(database_url)
    if path is not None and not path.is_file():
        raise FileNotFoundError(
            f"SQLite database not found at {path}. Set VERITY_DB_PATH (or "
            "VERITY_DATABASE_URL), or mount the database directory into the "
            "container, e.g. -v /path/to/db_dir:/db"
        )
