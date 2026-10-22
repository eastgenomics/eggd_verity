"""
Database initialisation for data pipeline.
"""

import logging

from data.database import get_engine, redact_database_url, resolve_database_url, sqlite_file_path

logger = logging.getLogger(__name__)

engine = get_engine()


def create_db_and_tables() -> None:
    """
    Ensures the SQLite database directory exists.
    Table creation and migration is by Alembic.
    """
    database_url = resolve_database_url()
    logger.info(f"Using database {redact_database_url(database_url)}")

    path = sqlite_file_path(database_url)
    if path is not None and not path.parent.exists():
        logger.info(f"Creating database directory at {path.parent}")
        path.parent.mkdir(exist_ok=True, parents=True)
