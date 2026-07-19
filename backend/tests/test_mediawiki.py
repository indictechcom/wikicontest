"""
Tests for MediaWiki API endpoints and fetch_article_metrics helper.
"""

import pytest
import requests
from unittest.mock import patch, MagicMock


class TestFetchArticleMetrics:
    """Tests for the fetch_article_metrics parallel helper."""

    def test_fetch_article_metrics_parallel(self, db, mock_mediawiki):
        """fetch_article_metrics should return a dict with all metric keys."""
        from app.utils import fetch_article_metrics
        with patch("app.utils.get_article_wikitext", return_value="Test wikitext"):
            with patch("app.utils.get_article_reference_count", return_value=5):
                with patch("app.utils.get_detailed_reference_counts", return_value={"new": 3, "reused": 2}):
                    with patch("app.utils.get_article_image_count", return_value=4):
                        with patch("app.utils.get_article_infobox_count", return_value=1):
                            with patch("app.utils.get_article_incoming_links", return_value=10):
                                with patch("app.utils.get_article_outgoing_links", return_value=7):
                                    from flask import Flask
                                    app = Flask(__name__)
                                    with app.app_context():
                                        result = fetch_article_metrics("https://en.wikipedia.org/wiki/Test")

        assert "reference_count" in result
        assert "new_ref_count" in result
        assert "reused_ref_count" in result
        assert "image_count" in result
        assert "infobox_count" in result
        assert "incoming_links" in result
        assert "outgoing_links" in result

    def test_fetch_article_metrics_partial_failure(self, db):
        """If one metric fails, others should still succeed."""
        from app.utils import fetch_article_metrics
        with patch("app.utils.get_article_wikitext", return_value="Test wikitext"):
            with patch("app.utils.get_article_reference_count", side_effect=Exception("API timeout")):
                with patch("app.utils.get_detailed_reference_counts", return_value={"new": 3, "reused": 2}):
                    with patch("app.utils.get_article_image_count", return_value=4):
                        with patch("app.utils.get_article_infobox_count", return_value=1):
                            with patch("app.utils.get_article_incoming_links", return_value=10):
                                with patch("app.utils.get_article_outgoing_links", return_value=7):
                                    from flask import Flask
                                    app = Flask(__name__)
                                    with app.app_context():
                                        result = fetch_article_metrics("https://en.wikipedia.org/wiki/Test")

        # Failed metric should be None, others should have values
        assert result["reference_count"] is None
        assert result["image_count"] == 4

    def test_fetch_article_metrics_wikitext_cached(self, db):
        """get_article_wikitext should be called only once, not per-metric."""
        from app.utils import fetch_article_metrics
        with patch("app.utils.get_article_wikitext", return_value="Test wikitext") as mock_wt:
            with patch("app.utils.get_article_reference_count", return_value=5):
                with patch("app.utils.get_detailed_reference_counts", return_value={"new": 3, "reused": 2}):
                    with patch("app.utils.get_article_image_count", return_value=4):
                        with patch("app.utils.get_article_infobox_count", return_value=1):
                            with patch("app.utils.get_article_incoming_links", return_value=10):
                                with patch("app.utils.get_article_outgoing_links", return_value=7):
                                    from flask import Flask
                                    app = Flask(__name__)
                                    with app.app_context():
                                        fetch_article_metrics("https://en.wikipedia.org/wiki/Test")

        # get_article_wikitext should be called exactly once
        assert mock_wt.call_count == 1


class TestMediaWikiArticleInfoEndpoint:
    """Tests for the /api/mediawiki/article-info endpoint."""

    def test_article_info_rejects_non_wiki_domain(self, client):
        resp = client.get("/api/mediawiki/article-info?url=https://evil.com/page")
        assert resp.status_code == 400

    def test_article_info_api_error_returns_502(self, client, monkeypatch):
        """If MediaWiki API returns an error, endpoint should return 502."""
        def fake_get(*args, **kwargs):
            resp = MagicMock()
            resp.status_code = 500
            resp.text = "Internal Server Error"
            return resp
        monkeypatch.setattr("requests.get", fake_get)
        resp = client.get("/api/mediawiki/article-info?url=https://en.wikipedia.org/wiki/Test")
        assert resp.status_code in (502, 500)


class TestMediaWikiClient:
    """Tests for the MediaWikiClient service class."""

    def test_get_returns_none_on_request_exception(self, monkeypatch):
        from app.services.mediawiki import MediaWikiClient

        def fake_get(*args, **kwargs):
            raise requests.RequestException("Network error")

        monkeypatch.setattr("requests.get", fake_get)
        client = MediaWikiClient()
        result = client.get("https://en.wikipedia.org/w/api.php", params={})
        assert result is None

    def test_get_returns_none_on_http_error(self, monkeypatch):
        from app.services.mediawiki import MediaWikiClient

        def fake_get(*args, **kwargs):
            resp = MagicMock()
            resp.status_code = 500
            resp.text = "Server Error"
            return resp

        monkeypatch.setattr("requests.get", fake_get)
        client = MediaWikiClient()
        result = client.get("https://en.wikipedia.org/w/api.php", params={})
        assert result is None

    def test_get_returns_none_on_api_error(self, monkeypatch):
        from app.services.mediawiki import MediaWikiClient

        def fake_get(*args, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"error": {"info": "Unknown page"}}
            return resp

        monkeypatch.setattr("requests.get", fake_get)
        client = MediaWikiClient()
        result = client.get("https://en.wikipedia.org/w/api.php", params={})
        assert result is None

    def test_get_returns_data_on_success(self, monkeypatch):
        from app.services.mediawiki import MediaWikiClient

        def fake_get(*args, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"query": {"pages": [{"pageid": 1}]}}
            return resp

        monkeypatch.setattr("requests.get", fake_get)
        client = MediaWikiClient()
        result = client.get("https://en.wikipedia.org/w/api.php", params={})
        assert result == {"query": {"pages": [{"pageid": 1}]}}

    def test_post_returns_none_on_request_exception(self, monkeypatch):
        from app.services.mediawiki import MediaWikiClient

        def fake_post(*args, **kwargs):
            raise requests.RequestException("Network error")

        monkeypatch.setattr("requests.post", fake_post)
        client = MediaWikiClient()
        result = client.post("https://en.wikipedia.org/w/api.php", data={})
        assert result is None
