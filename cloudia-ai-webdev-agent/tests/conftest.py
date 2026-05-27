"""
conftest.py — shared fixtures for CloudIA test suite.

Uses SQLite in-memory for all tests. Environment variables are set before any
backend module is imported so that pydantic-settings picks them up correctly.
"""

import os
import pytest
from cryptography.fernet import Fernet

# ---------------------------------------------------------------------------
# Set env vars FIRST — before any backend import
# ---------------------------------------------------------------------------

# Generate a valid Fernet key once for the entire test session
_FERNET_KEY = Fernet.generate_key().decode()

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test_secret_key_32_chars_xxxxxxxx")
os.environ["ENCRYPTION_KEY"] = _FERNET_KEY  # Always override with valid key
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-fake-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Imports (only after env vars are set)
# ---------------------------------------------------------------------------

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Ensure env vars remain set for the whole test session."""
    # Already set at module level — this fixture documents the requirement
    # and provides a hook for teardown if needed.
    yield


@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh in-memory SQLite engine per test function.

    StaticPool forces all connections to share one underlying SQLite connection,
    so the in-memory database persists across threads (needed by TestClient).
    """
    from backend.db.models import Base

    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_fk(dbapi_conn, _rec):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db(db_engine):
    """Provide a transactional session that rolls back after each test."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(db):
    """FastAPI TestClient with the test DB session injected."""
    from fastapi.testclient import TestClient
    from backend.db.session import get_session
    from backend.api.app import app

    def override_get_session():
        yield db

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def api_headers():
    """Standard API key header for all authenticated routes."""
    return {"X-API-Key": "test_secret_key_32_chars_xxxxxxxx"}
