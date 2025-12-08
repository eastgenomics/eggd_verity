"""
Database initialisation for data pipeline.
"""

import logging

from sqlmodel import create_engine

from data.config import DATABASE_PATH

logger = logging.getLogger(__name__)

engine = create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"timeout": 60})


def create_db_and_tables() -> None:
    """
    Ensures the database directory exists.
    Table creation and migration is by Alembic.
    """
    if not DATABASE_PATH.parent.exists():
        logger.info(f"Creating database directory at {DATABASE_PATH.parent}")
        DATABASE_PATH.parent.mkdir(exist_ok=True, parents=True)
