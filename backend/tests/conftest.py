"""
Shared pytest fixtures for the SparqAI backend test suite.

Uses an in-memory SQLite database so tests are fast, isolated, and
require no external infrastructure.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.core.security import get_password_hash, create_access_token
from backend.app import models


# ---------------------------------------------------------------------------
# In-memory SQLite engine (shared across all test modules)
# ---------------------------------------------------------------------------

SQLALCHEMY_DATABASE_URL = "sqlite://"

_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_db():
    """
    Provide a clean database session for each test.

    Creates all tables before the test and drops them afterward so every
    test starts with a blank slate.
    """
    Base.metadata.create_all(bind=_engine)
    connection = _engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    Base.metadata.drop_all(bind=_engine)


# Keep the old name as an alias so existing tests that use `db` still work.
@pytest.fixture(scope="function")
def db(test_db):
    """Alias for test_db -- backwards compatibility with older tests."""
    return test_db


@pytest.fixture(scope="function")
def test_client(test_db):
    """
    FastAPI TestClient wired to the in-memory test database.

    Overrides the production ``get_db`` dependency so every HTTP request
    issued through this client hits the same in-memory SQLite session.
    """

    def _override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


# Keep the old name as an alias so existing tests that use `client` still work.
@pytest.fixture(scope="function")
def client(test_client):
    """Alias for test_client -- backwards compatibility with older tests."""
    return test_client


@pytest.fixture(scope="function")
def test_user(test_db) -> models.User:
    """
    Create and return a test user with an associated organization.

    The user is the first member of the organization and is therefore
    assigned the ``ADMIN`` role, matching the real registration flow.
    """
    org = models.Organization(name="Test Organization")
    test_db.add(org)
    test_db.flush()

    user = models.User(
        email="testuser@sparqai.com",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Test User",
        organization_id=org.id,
        role="ADMIN",
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user) -> dict:
    """
    Return a dict with a valid ``Authorization: Bearer <token>`` header
    for the ``test_user`` fixture.
    """
    token = create_access_token(
        data={"sub": test_user.email, "org_id": test_user.organization_id}
    )
    return {"Authorization": f"Bearer {token}"}
