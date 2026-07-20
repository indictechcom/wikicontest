"""
Pytest configuration and shared fixtures for WikiEval backend tests.

Run with: cd backend && pytest
"""

import importlib
import os
import sys

# Ensure the backend package is importable when running pytest from the backend dir.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# MUST set testing env var BEFORE importing app so the module-level
# app = create_app() picks up TestingConfig.
os.environ["FLASK_ENV"] = "testing"

import pytest
from unittest.mock import MagicMock

# Import the module-level app which already has all blueprints and routes.
# app/__init__.py calls load_dotenv() at module level, which reloads the .env
# file. We therefore pop the secret keys AFTER importing the app (so the
# running app keeps its real secrets) and reload app.config so its class-level
# defaults are recomputed with those env vars unset.
from app import app as _app  # noqa: E402

os.environ.pop("DATABASE_URL", None)
os.environ.pop("SECRET_KEY", None)
os.environ.pop("JWT_SECRET_KEY", None)

import app.config as _config_module  # noqa: E402
importlib.reload(_config_module)


@pytest.fixture(scope="session")
def app():
    """
    Provide the configured Flask application used by tests.
    
    Returns:
        Flask: The module-level Flask application.
    """
    return _app


# ---------------------------------------------------------------------------
# Database fixture (function-scoped — fresh DB per test)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function", autouse=True)
def db(app):
    """
    Manage the test database lifecycle for each test.
    
    Yields:
    	db: The configured database object.
    """
    from app.database import db as _db

    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(autouse=True)
def _disable_rate_limiting(app):
    """
    Disable rate limiting during a test and restore it afterward.
    """
    with app.app_context():
        from app.extensions import limiter
        limiter.enabled = False
        yield
        limiter.enabled = True


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(app, db):
    """
    Create a Flask test client configured for application testing.
    
    Returns:
    	FlaskClient: A client for sending requests to the Flask application.
    """
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """
    Register and authenticate a standard test user for API requests.
    
    Returns:
        The test client with authentication state established.
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
    Create an administrator user, authenticate it, and prepare the client for authenticated requests.
    
    Returns:
        client: The client with an administrator's JWT access token cookie.
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
    Replace `requests.get` and `requests.post` with recorded test doubles that return predefined MediaWiki responses.
    
    Parameters:
    	monkeypatch: Pytest monkeypatch fixture used to replace the HTTP request functions.
    
    Returns:
    	dict: A mapping containing the `get` and `post` mocks for asserting request calls.
    """
    mock_get = MagicMock()
    mock_post = MagicMock()

    def fake_get(url, **kwargs):
        """
        Provide a mocked response for MediaWiki query and parse requests.
        
        Parameters:
            kwargs: Request arguments containing optional MediaWiki action and title parameters.
        
        Returns:
            A mocked response containing the matching fixture data, or a 404 response for unsupported requests.
        """
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
        """Return a successful mock response for a MediaWiki POST request.
        
        Parameters:
            url (str): The request URL.
            **kwargs: Additional request arguments recorded by the mock.
        
        Returns:
            MagicMock: A response with a 200 status code and a success result body.
        """
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
