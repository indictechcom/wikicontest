"""
Tests for user dashboard and trusted member endpoints.
"""

import pytest
from unittest.mock import patch

from app.database import db


class TestDashboard:
    """Tests for /api/user/dashboard."""

    def test_dashboard_returns_organized_contests(self, client, db, factories):
        user = factories.create_user(username="dash_org", email="dash_org@example.com", is_trusted_member=True)
        factories.create_contest(created_by="dash_org")
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.get("/api/user/dashboard")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "organized_contests" in data
        assert len(data["organized_contests"]) >= 1

    def test_dashboard_access_organizer(self, client, db, factories):
        user = factories.create_user(username="access_org", email="access_org@example.com", is_trusted_member=True)
        factories.create_contest(created_by="access_org")
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.get("/api/user/dashboard/access")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["can_access_organizer"] is True

    def test_dashboard_access_non_organizer(self, client, db, factories):
        user = factories.create_user(username="access_none", email="access_none@example.com")
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.get("/api/user/dashboard/access")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["can_access_organizer"] is False

    def test_dashboard_access_trusted_member(self, client, db, factories):
        user = factories.create_user(username="access_trusted", email="access_trusted@example.com", is_trusted_member=True)
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.get("/api/user/dashboard/access")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["can_access_organizer"] is True


class TestTrustedMemberRequest:
    """Tests for trusted member request/approve/reject flow.

    The request_trusted_member endpoint requires:
    1. User has OAuth tokens (oauth_token and oauth_token_secret)
    2. MediaWiki API edit count check

    We mock get_mediawiki_user_edit_count to return 50 (below 300 threshold)
    so the request goes to 'pending' status for superadmin review.
    """

    def _create_oauth_user(self, factories, username, email):
        user = factories.create_user(username=username, email=email)
        user.oauth_token = "test_token"
        user.oauth_token_secret = "test_secret"
        user.save()
        return user

    @patch("app.utils.get_mediawiki_user_edit_count", return_value=50)
    def test_request_trusted_member(self, mock_edit_count, client, db, factories):
        user = self._create_oauth_user(factories, "tm_request", "tm_request@example.com")
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.post("/api/user/trusted-members/request", json={"reason": "I want to create contests"})
        print(f"RESP: {resp.status_code} {resp.get_json()}")
        assert resp.status_code == 200

    @patch("app.utils.get_mediawiki_user_edit_count", return_value=50)
    def test_duplicate_trusted_member_request_blocked(self, mock_edit_count, client, db, factories):
        user = self._create_oauth_user(factories, "tm_dup", "tm_dup@example.com")
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp1 = client.post("/api/user/trusted-members/request", json={"reason": "Please"})
        assert resp1.status_code == 200
        resp2 = client.post("/api/user/trusted-members/request", json={"reason": "Again"})
        assert resp2.status_code == 400

    @patch("app.utils.get_mediawiki_user_edit_count", return_value=50)
    def test_approve_trusted_member(self, mock_edit_count, client, db, factories):
        user = self._create_oauth_user(factories, "tm_approve", "tm_approve@example.com")
        admin = factories.create_user(username="tm_admin", email="tm_admin@example.com", role="superadmin")

        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.post("/api/user/trusted-members/request", json={"reason": "I need access"})
        assert resp.status_code == 200

        client.post("/api/user/login", json={"email": admin.email, "password": "TestPass123!"})
        resp = client.post(f"/api/user/trusted-members/{user.id}/approve")
        assert resp.status_code == 200

        from app.models.user import User
        from app.models.trusted_member_request import TrustedMemberRequest
        updated = db.session.get(User, user.id)
        assert updated.is_trusted_member is True

        latest_request = TrustedMemberRequest.query.filter_by(
            user_id=user.id
        ).order_by(TrustedMemberRequest.created_at.desc()).first()
        assert latest_request is not None
        assert latest_request.status == "approved"

    @patch("app.utils.get_mediawiki_user_edit_count", return_value=50)
    def test_reject_trusted_member(self, mock_edit_count, client, db, factories):
        user = self._create_oauth_user(factories, "tm_reject", "tm_reject@example.com")
        admin = factories.create_user(username="tm_rej_admin", email="tm_rej_admin@example.com", role="superadmin")

        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.post("/api/user/trusted-members/request", json={"reason": "Please"})
        assert resp.status_code == 200

        client.post("/api/user/login", json={"email": admin.email, "password": "TestPass123!"})
        resp = client.post(f"/api/user/trusted-members/{user.id}/reject")
        assert resp.status_code == 200

        from app.models.user import User
        from app.models.trusted_member_request import TrustedMemberRequest
        updated = db.session.get(User, user.id)
        assert updated.is_trusted_member is False
        latest_request = TrustedMemberRequest.query.filter_by(
            user_id=user.id
        ).order_by(TrustedMemberRequest.created_at.desc()).first()
        assert latest_request is not None
        assert latest_request.status == "rejected"

    @patch("app.utils.get_mediawiki_user_edit_count", return_value=50)
    def test_non_superadmin_cannot_approve(self, mock_edit_count, client, db, factories):
        user = self._create_oauth_user(factories, "tm_noapprove", "tm_noapprove@example.com")
        regular_admin = factories.create_user(username="tm_reg_admin", email="tm_reg_admin@example.com", role="admin")

        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.post("/api/user/trusted-members/request", json={"reason": "Please"})
        assert resp.status_code == 200

        client.post("/api/user/login", json={"email": regular_admin.email, "password": "TestPass123!"})
        resp = client.post(f"/api/user/trusted-members/{user.id}/approve")
        assert resp.status_code == 403
