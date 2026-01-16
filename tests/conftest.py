import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Import models to ensure they are registered with SQLModel.metadata
from data.models import reports  # noqa: F401


@pytest.fixture(name="session")
def session_fixture():
    """
    Creates an in-memory SQLite database and returns a session for testing.
    Using StaticPool ensures the same in-memory database is shared across the session.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
