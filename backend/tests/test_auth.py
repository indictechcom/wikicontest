"""
P0 Backend Tests — Auth & RBAC
"""

import pytest


class TestRegister:
    def test_register_valid(self, client, db):
        resp = client.post(
            "/api/user/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123!",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["username"] == "newuser"

    def test_register_duplicate_email(self, client, db):
        client.post(
            "/api/user/register",
            json={
                "username": "user1",
                "email": "dup@example.com",
                "password": "Pass123!",
            },
        )
        resp = client.post(
            "/api/user/register",
            json={
                "username": "user2",
                "email": "dup@example.com",
                "password": "Pass123!",
            },
        )
        assert resp.status_code == 400

    def test_register_missing_fields(self, client, db):
        resp = client.post("/api/user/register", json={})
        assert resp.status_code == 400

    def test_register_xss_in_username(self, client, db):
        resp = client.post(
            "/api/user/register",
            json={
                "username": "<script>alert(1)</script>",
                "email": "xss@example.com",
                "password": "Pass123!",
            },
        )
        assert resp.status_code in (400, 201)
        if resp.status_code == 201:
            data = resp.get_json()
            assert "<script>" not in data.get("user", {}).get("username", "")


class TestLogin:
    def test_login_valid(self, client, db):
        client.post(
            "/api/user/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "password": "Pass123!",
            },
        )
        resp = client.post(
            "/api/user/login",
            json={"email": "login@example.com", "password": "Pass123!"},
        )
        assert resp.status_code == 200
        assert "access_token_cookie" in resp.headers.get("Set-Cookie", "")

    def test_login_wrong_password(self, client, db):
        client.post(
            "/api/user/register",
            json={
                "username": "wpuser",
                "email": "wp@example.com",
                "password": "Pass123!",
            },
        )
        resp = client.post(
            "/api/user/login",
            json={"email": "wp@example.com", "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client, db):
        resp = client.post(
            "/api/user/login",
            json={"email": "nonexistent@example.com", "password": "Pass123!"},
        )
        assert resp.status_code == 401


class TestLogout:
    def test_logout_clears_cookie(self, auth_client):
        resp = auth_client.post("/api/user/logout")
        assert resp.status_code == 200
        check = auth_client.get("/api/cookie")
        assert check.status_code == 401


class TestAuthMiddleware:
    def test_require_auth_blocks_anonymous(self, client):
        resp = client.get("/api/user/dashboard")
        assert resp.status_code == 401

    def test_require_role_blocks_user(self, client, db):
        from app.models.user import User
        user = User(username="regular", email="regular@example.com", password="Pass123!", role="user")
        user.save()
        client.post("/api/user/login", json={"email": "regular@example.com", "password": "Pass123!"})
        resp = client.get("/api/user/all")
        assert resp.status_code == 403

    def test_require_role_allows_admin(self, admin_client):
        resp = admin_client.get("/api/user/all")
        assert resp.status_code == 200

    def test_admin_bypasses_role_check(self, client, db):
        from app.models.user import User
        admin = User(username="admin2", email="admin2@example.com", password="Pass123!", role="admin")
        admin.save()
        client.post("/api/user/login", json={"email": "admin2@example.com", "password": "Pass123!"})
        resp = client.get("/api/user/all")
        assert resp.status_code == 200


class TestHealthCheck:
    def test_health_check_returns_healthy(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
