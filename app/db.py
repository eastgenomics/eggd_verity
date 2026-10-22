from sqlmodel import Session

from data.database import ensure_database_available, get_engine, resolve_database_url


def get_session() -> Session:
    database_url = resolve_database_url()
    ensure_database_available(database_url)
    return Session(get_engine(database_url))
