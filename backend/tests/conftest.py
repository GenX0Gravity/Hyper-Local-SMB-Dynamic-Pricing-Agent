import pytest
from sqlmodel import SQLModel, create_engine, Session
from backend.core.database import engine as db_engine

@pytest.fixture(name="session")
def session_fixture():
    # Use SQLite in-memory for unit testing
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
