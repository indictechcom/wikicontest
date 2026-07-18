"""
P0 Backend Tests — Submission CRUD
"""

import pytest
from datetime import date, timedelta


class TestSubmissionCRUD:
    def test_submit_article_valid(self, client, db, factories, mock_mediawiki):
        user = factories.create_user(username="submit_user", email="submit_user@example.com", is_trusted_member=True)
        contest = factories.create_contest(created_by="submit_user")
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.post(
            f"/api/contest/{contest.id}/submit",
            json={"article_link": "https://en.wikipedia.org/wiki/Test_Article"},
        )
        assert resp.status_code == 201

    def test_submit_article_duplicate(self, client, db, factories, mock_mediawiki):
        user = factories.create_user(username="dup_user", email="dup_user@example.com", is_trusted_member=True)
        contest = factories.create_contest(created_by="dup_user")
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        link = "https://en.wikipedia.org/wiki/Test_Article"
        client.post(f"/api/contest/{contest.id}/submit", json={"article_link": link})
        resp = client.post(f"/api/contest/{contest.id}/submit", json={"article_link": link})
        assert resp.status_code == 400

    def test_submit_article_invalid_url(self, client, db, factories):
        user = factories.create_user(username="inv_user", email="inv_user@example.com", is_trusted_member=True)
        contest = factories.create_contest(created_by="inv_user")
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.post(
            f"/api/contest/{contest.id}/submit",
            json={"article_link": "not-a-url"},
        )
        assert resp.status_code == 400

    def test_get_submission_by_id(self, client, db, factories, mock_mediawiki):
        user = factories.create_user(username="get_user", email="get_user@example.com", is_trusted_member=True)
        contest = factories.create_contest(created_by="get_user")
        submission = factories.create_submission(user_id=user.id, contest_id=contest.id)
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.get(f"/api/submission/{submission.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == submission.id

    def test_delete_submission_as_admin(self, admin_client, db, factories):
        user = factories.create_user(username="del_user", email="del_user@example.com")
        contest = factories.create_contest()
        submission = factories.create_submission(user_id=user.id, contest_id=contest.id)
        resp = admin_client.delete(f"/api/submission/{submission.id}")
        assert resp.status_code == 200

    def test_review_submission_accepted(self, client, db, factories, mock_mediawiki):
        jury = factories.create_user(username="jury_user", email="jury_user@example.com")
        user = factories.create_user(username="submit_user2", email="submit_user2@example.com", is_trusted_member=True)
        contest = factories.create_contest(created_by="submit_user2", jury_members=["jury_user"])
        factories.create_submission(user_id=user.id, contest_id=contest.id)
        client.post("/api/user/login", json={"email": jury.email, "password": "TestPass123!"})
        submission = contest.submissions.first()
        resp = client.put(
            f"/api/submission/{submission.id}/review",
            json={"status": "accepted", "score": 10},
        )
        assert resp.status_code == 200

    def test_review_submission_non_jury_blocked(self, client, db, factories):
        outsider = factories.create_user(username="outsider2", email="outsider2@example.com")
        user = factories.create_user(username="submit_user3", email="submit_user3@example.com", is_trusted_member=True)
        contest = factories.create_contest(created_by="submit_user3")
        factories.create_submission(user_id=user.id, contest_id=contest.id)
        client.post("/api/user/login", json={"email": outsider.email, "password": "TestPass123!"})
        submission = contest.submissions.first()
        resp = client.put(
            f"/api/submission/{submission.id}/review",
            json={"status": "accepted"},
        )
        assert resp.status_code == 403
