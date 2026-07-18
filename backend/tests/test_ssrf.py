"""
P0 Backend Tests — SSRF Protection
"""

import pytest
from app.utils.url_validation import validate_wiki_url


class TestValidateWikiUrl:
    def test_valid_english_wikipedia(self):
        base_url, error = validate_wiki_url("https://en.wikipedia.org/wiki/Test_Article")
        assert error is None
        assert base_url == "https://en.wikipedia.org"

    def test_valid_wikidata(self):
        base_url, error = validate_wiki_url("https://www.wikidata.org/wiki/Q123")
        assert error is None
        assert base_url == "https://www.wikidata.org"

    def test_valid_multilingual_wikipedia(self):
        base_url, error = validate_wiki_url("https://hi.wikipedia.org/wiki/परीक्षा")
        assert error is None
        assert base_url == "https://hi.wikipedia.org"

    def test_valid_mediawiki_org(self):
        base_url, error = validate_wiki_url("https://www.mediawiki.org/wiki/MediaWiki")
        assert error is None

    def test_rejects_cloud_metadata_ip(self):
        base_url, error = validate_wiki_url("http://169.254.169.254/latest/meta-data/")
        assert error is not None
        assert error[1] == 400

    def test_rejects_internal_service(self):
        base_url, error = validate_wiki_url("http://internal-service:8080/api")
        assert error is not None
        assert error[1] == 400

    def test_rejects_non_wiki_domain(self):
        base_url, error = validate_wiki_url("https://evil.com/wiki/Fake")
        assert error is not None
        assert error[1] == 400

    def test_rejects_url_encoding_trick(self):
        base_url, error = validate_wiki_url("https://en.wikipedia.org%40evil.com/wiki/X")
        assert error is not None
        assert error[1] == 400

    def test_rejects_ftp_scheme(self):
        base_url, error = validate_wiki_url("ftp://en.wikipedia.org/wiki/X")
        assert error is not None
        assert error[1] == 400

    def test_rejects_empty_url(self):
        base_url, error = validate_wiki_url("")
        assert error is not None
        assert error[1] == 400

    def test_rejects_none(self):
        base_url, error = validate_wiki_url(None)
        assert error is not None


class TestSSRFInArticleInfoEndpoint:
    def test_article_info_rejects_ssrf(self, client, mock_mediawiki):
        resp = client.get(
            "/api/mediawiki/article-info",
            query_string={"url": "http://169.254.169.254/latest/meta-data/"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_article_info_accepts_valid_wiki(self, client, mock_mediawiki):
        resp = client.get(
            "/api/mediawiki/article-info",
            query_string={"url": "https://en.wikipedia.org/wiki/Test_Article"},
        )
        assert resp.status_code == 200
