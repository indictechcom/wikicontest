"""
Pytest configuration and shared fixtures for WikiContest backend tests.

Run with: cd backend && pytest
"""

import os
import sys

# Ensure the backend package is importable when running pytest from the backend dir.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# MUST set testing env vars BEFORE importing app so the module-level
# app = create_app() picks up TestingConfig.
os.environ["FLASK_ENV"] = "testing"
os.environ.pop("DATABASE_URL", None)
os.environ.pop("SECRET_KEY", None)
os.environ.pop("JWT_SECRET_KEY", None)

import pytest
from unittest.mock import MagicMock

# Import the module-level app which already has all blueprints and routes.
from app import app as _app  # noqa: E402


@pytest.fixture(scope="session")
def app():
    """Return the module-level Flask app (already configured with TestingConfig)."""
    return _app


# ---------------------------------------------------------------------------
# Database fixture (function-scoped — fresh DB per test)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function", autouse=True)
def db(app):
    """
    Create all tables before each test and drop them after.
    Rolls back any pending transactions on teardown.
    """
    from app.database import db as _db

    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(autouse=True)
def _disable_rate_limiting(app):
    """Disable flask-limiter for every test to avoid 429 interference."""
    with app.app_context():
        from app import limiter
        limiter.enabled = False
        yield
        limiter.enabled = True


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(app, db):
    """Flask test client with in-memory SQLite and JWT cookies enabled."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """
    Register a test user, log them in, and return the client with a valid
    JWT access_token cookie already set.
    """
    register_resp = client.post(
        "/api/user/register",
        json={
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "TestPass123!",
        },
    )
    login_resp = client.post(
        "/api/user/login",
        json={
            "email": "testuser@example.com",
            "password": "TestPass123!",
        },
    )
    if login_resp.status_code != 200:
        print(f"[DEBUG] auth_client login failed: {login_resp.status_code} {login_resp.get_json()}")
    return client


@pytest.fixture
def admin_client(client):
    """
    Create an admin user, log them in, and return the client with a valid
    JWT access_token cookie.
    """
    from app.models.user import User

    admin = User(username="adminuser", email="admin@example.com", password="AdminPass123!", role="admin")
    admin.save()

    client.post(
        "/api/user/login",
        json={
            "email": "admin@example.com",
            "password": "AdminPass123!",
        },
    )
    return client


# ---------------------------------------------------------------------------
# MediaWiki mock fixture
# ---------------------------------------------------------------------------

_MEDIAWIKI_REVISIONS_RESPONSE = {
    "query": {
        "pages": [
            {
                "pageid": 12345,
                "ns": 0,
                "title": "Test Article",
                "revisions": [
                    {
                        "user": "TestUser",
                        "userid": 1,
                        "timestamp": "2024-01-15T10:00:00Z",
                        "size": 5000,
                    }
                ],
            }
        ]
    }
}

_MEDIAWIKI_MISSING_RESPONSE = {
    "query": {
        "pages": [
            {
                "pageid": -1,
                "ns": 0,
                "title": "Dup_Article",
                "missing": True,
            }
        ]
    }
}

_MEDIAWIKI_PARSE_RESPONSE = {
    "parse": {
        "title": "Test Article",
        "displaytitle": "Test Article",
        "text": {"*": "<p>Test content</p>"},
    }
}


@pytest.fixture
def mock_mediawiki(monkeypatch):
    """
    Monkeypatch requests.get / requests.post so no real HTTP calls are made
    during tests. Returns a MagicMock that records call arguments for
    assertions.
    """
    mock_get = MagicMock()
    mock_post = MagicMock()

    def fake_get(url, **kwargs):
        mock_get(url, **kwargs)
        params = kwargs.get("params", {})
        if not isinstance(params, dict):
            params = {}
        if params.get("action") == "query":
            titles = params.get("titles", "")
            if "Test_Article" in str(titles) or "Test Article" in str(titles):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = _MEDIAWIKI_REVISIONS_RESPONSE
                resp.text = '{"query":{}}'
                return resp
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = _MEDIAWIKI_MISSING_RESPONSE
            resp.text = '{"query":{}}'
            return resp
        if params.get("action") == "parse":
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = _MEDIAWIKI_PARSE_RESPONSE
            resp.text = '{"parse":{}}'
            return resp
        resp = MagicMock()
        resp.status_code = 404
        resp.text = "Not Found"
        return resp

    def fake_post(url, **kwargs):
        mock_post(url, **kwargs)
        resp = MagicMock()
        resp.status_code = 200
        resp.text = '{"result": "success"}'
        return resp

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.post", fake_post)

    return {"get": mock_get, "post": mock_post}


# ---------------------------------------------------------------------------
# Factory fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def factories():
    """Expose test factory functions as a convenient namespace."""
    from tests.factories import create_user, create_contest, create_submission
    import types
    ns = types.SimpleNamespace(
        create_user=create_user,
        create_contest=create_contest,
        create_submission=create_submission,
    )
    return ns
