"""
Tests for app/config.py — centralized configuration management.

This PR renamed the project from "WikiContest" to "WikiEval". These tests
lock in the renamed defaults (secret keys, database names, app metadata)
and verify the Toolforge / SQLite database-URL derivation logic that
embeds the new project name.
"""

import importlib
import os

import pytest

from app.config import (
    Config,
    DevelopmentConfig,
    TestingConfig,
    ProductionConfig,
    config as config_map,
    get_config,
)


class TestBaseConfigDefaults:
    """Defaults on the base Config class reflect the WikiEval rename."""

    def test_app_name_is_wikieval(self):
        assert Config.APP_NAME == "WikiEval"

    def test_app_name_does_not_reference_old_project_name(self):
        assert "WikiContest" not in Config.APP_NAME
        assert "wikicontest" not in Config.APP_NAME.lower()

    def test_secret_key_default_uses_wikieval_prefix(self):
        # conftest.py pops SECRET_KEY from the environment before the app
        # (and therefore app.config) is imported, so the class-level
        # default computed via os.getenv(..., default) is what's active.
        assert Config.SECRET_KEY == "wikieval-dev-secret-key"

    def test_jwt_secret_key_default_uses_wikieval_prefix(self):
        assert Config.JWT_SECRET_KEY == "wikieval-jwt-secret-key"

    def test_secret_keys_do_not_reference_old_project_name(self):
        assert "wikicontest" not in Config.SECRET_KEY.lower()
        assert "wikicontest" not in Config.JWT_SECRET_KEY.lower()

    def test_app_version_and_description_present(self):
        assert Config.APP_VERSION == "1.0.0"
        assert isinstance(Config.APP_DESCRIPTION, str)
        assert Config.APP_DESCRIPTION  # non-empty


class TestEnvironmentConfigClasses:
    """Environment-specific configs inherit the renamed base defaults."""

    @pytest.mark.parametrize("cls", [DevelopmentConfig, TestingConfig, ProductionConfig])
    def test_inherits_app_name(self, cls):
        assert cls.APP_NAME == "WikiEval"

    def test_development_config_debug_enabled(self):
        assert DevelopmentConfig.DEBUG is True

    def test_testing_config_uses_in_memory_sqlite(self):
        assert TestingConfig.SQLALCHEMY_DATABASE_URI == "sqlite:///:memory:"

    def test_testing_config_disables_csrf(self):
        assert TestingConfig.JWT_COOKIE_CSRF_PROTECT is False

    def test_production_config_requires_secure_cookies(self):
        assert ProductionConfig.JWT_COOKIE_SECURE is True
        assert ProductionConfig.DEBUG is False


class TestGetConfig:
    """get_config() resolves the correct configuration class by name."""

    def test_get_config_development(self):
        assert get_config("development") is DevelopmentConfig

    def test_get_config_testing(self):
        assert get_config("testing") is TestingConfig

    def test_get_config_production(self):
        assert get_config("production") is ProductionConfig

    def test_get_config_unknown_environment_falls_back_to_default(self):
        assert get_config("totally-unknown-env") is config_map["default"]

    def test_get_config_uses_flask_env_when_no_argument_given(self, monkeypatch):
        """Verify that `get_config` uses the `FLASK_ENV` environment variable when no environment is provided."""
        monkeypatch.setenv("FLASK_ENV", "production")
        assert get_config() is ProductionConfig

    def test_config_map_default_is_development(self):
        assert config_map["default"] is DevelopmentConfig


class TestDatabaseUrlDerivation:
    """
    Config computes SQLALCHEMY_DATABASE_URI at class-definition (import) time
    based on environment variables. To exercise the various branches
    (explicit DATABASE_URL, Toolforge auto-detection, SQLite fallback) the
    module must be reloaded with a controlled environment, then restored.
    """

    @pytest.fixture
    def reloaded_config(self, monkeypatch):
        """
        Provide a helper for reloading `app.config` after environment changes.
        
        Reloads the module again during fixture teardown to refresh its configuration state.
        """
        import app.config as config_module

        def _reload():
            importlib.reload(config_module)
            return config_module

        yield _reload

        # monkeypatch restores the environment automatically after the test
        # returns; reload once more here so any subsequent test relying on
        # the "real" test-session environment sees consistent class state.
        importlib.reload(config_module)

    def test_explicit_database_url_is_used_verbatim(self, monkeypatch, reloaded_config):
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/mydb")
        monkeypatch.delenv("TOOL_TOOLSDB_USER", raising=False)
        monkeypatch.delenv("TOOL_TOOLSDB_PASSWORD", raising=False)

        reloaded = reloaded_config()

        assert reloaded.Config.SQLALCHEMY_DATABASE_URI == "postgresql://user:pass@localhost/mydb"

    def test_toolforge_detection_defaults_db_name_to_wikieval(self, monkeypatch, reloaded_config):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("TOOL_TOOLSDB_USER", "s12345")
        monkeypatch.setenv("TOOL_TOOLSDB_PASSWORD", "supersecret")
        monkeypatch.delenv("TOOL_TOOLSDB_DBNAME", raising=False)

        reloaded = reloaded_config()

        uri = reloaded.Config.SQLALCHEMY_DATABASE_URI
        assert uri.startswith("mysql+pymysql://s12345:supersecret@")
        assert uri.endswith("/s12345__wikieval")

    def test_toolforge_detection_honors_explicit_db_name_override(self, monkeypatch, reloaded_config):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("TOOL_TOOLSDB_USER", "s12345")
        monkeypatch.setenv("TOOL_TOOLSDB_PASSWORD", "supersecret")
        monkeypatch.setenv("TOOL_TOOLSDB_DBNAME", "customdb")

        reloaded = reloaded_config()

        uri = reloaded.Config.SQLALCHEMY_DATABASE_URI
        assert uri.endswith("/s12345__customdb")
        assert "wikieval" not in uri

    def test_sqlite_fallback_used_when_no_database_url_or_toolforge_env(self, monkeypatch, reloaded_config):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("TOOL_TOOLSDB_USER", raising=False)
        monkeypatch.delenv("TOOL_TOOLSDB_PASSWORD", raising=False)

        reloaded = reloaded_config()

        assert reloaded.Config.SQLALCHEMY_DATABASE_URI == "sqlite:///wikieval_dev.db"

    def test_sqlite_fallback_does_not_reference_old_project_name(self, monkeypatch, reloaded_config):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("TOOL_TOOLSDB_USER", raising=False)
        monkeypatch.delenv("TOOL_TOOLSDB_PASSWORD", raising=False)

        reloaded = reloaded_config()

        assert "wikicontest" not in reloaded.Config.SQLALCHEMY_DATABASE_URI.lower()

    def test_toolforge_detection_requires_both_user_and_password(self, monkeypatch, reloaded_config):
        """If only one of the two Toolforge credentials is set, fall back to SQLite."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("TOOL_TOOLSDB_USER", "s12345")
        monkeypatch.delenv("TOOL_TOOLSDB_PASSWORD", raising=False)

        reloaded = reloaded_config()

        assert reloaded.Config.SQLALCHEMY_DATABASE_URI == "sqlite:///wikieval_dev.db"