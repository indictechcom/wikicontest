"""
P0 Backend Tests — Contest CRUD
"""

import pytest
from datetime import date, timedelta


class TestContestCRUD:
    def test_create_contest_as_trusted_user(self, auth_client, db, factories):
        user = factories.create_user(username="trusted_user", is_trusted_member=True)
        auth_client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = auth_client.post(
            "/api/contest",
            json={
                "name": "New Contest",
                "project_name": "TestProject",
                "jury_members": ["trusted_user"],
                "start_date": str(date.today() - timedelta(days=1)),
                "end_date": str(date.today() + timedelta(days=7)),
                "min_byte_count": 100,
            },
        )
        assert resp.status_code == 201

    def test_create_contest_as_regular_user_blocked(self, client, db, factories):
        user = factories.create_user(username="regular_user", email="regular_user@example.com")
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.post(
            "/api/contest",
            json={
                "name": "Should Fail",
                "project_name": "TestProject",
                "jury_members": ["some_user"],
            },
        )
        assert resp.status_code == 403

    def test_create_contest_missing_fields(self, auth_client):
        resp = auth_client.post("/api/contest", json={})
        assert resp.status_code == 400

    def test_list_contests_returns_categories(self, auth_client, db, factories):
        factories.create_contest()
        resp = auth_client.get("/api/contest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "current" in data
        assert "upcoming" in data
        assert "past" in data

    def test_update_contest_as_owner(self, client, db, factories):
        user = factories.create_user(username="owner_user", email="owner_user@example.com")
        contest = factories.create_contest(created_by="owner_user")
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.put(
            f"/api/contest/{contest.id}",
            json={"name": "Updated Contest"},
        )
        assert resp.status_code == 200

    def test_update_contest_as_non_owner_blocked(self, client, db, factories):
        owner = factories.create_user(username="owner2", email="owner2@example.com")
        attacker = factories.create_user(username="attacker2", email="attacker2@example.com")
        contest = factories.create_contest(created_by="owner2")
        client.post("/api/user/login", json={"email": attacker.email, "password": "TestPass123!"})
        resp = client.put(
            f"/api/contest/{contest.id}",
            json={"name": "Hacked Contest"},
        )
        assert resp.status_code == 403

    def test_delete_contest_as_admin(self, admin_client, db, factories):
        contest = factories.create_contest()
        resp = admin_client.delete(f"/api/contest/{contest.id}")
        assert resp.status_code == 200
