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
        # Response is now paginated: {"contests": {"current": [...], "past": [...], "upcoming": [...]}, "page": 1, ...}
        contests = data.get("contests", data)  # Support both old and new format
        assert "current" in contests
        assert "upcoming" in contests
        assert "past" in contests

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


class TestContestScoringModeLock:
    def test_update_contest_blocks_scoring_mode_change_with_accepted_submissions(
        self, client, db, factories
    ):
        owner = factories.create_user(
            username="owner_acc", email="owner_acc@example.com", is_trusted_member=True
        )
        contest = factories.create_contest(created_by="owner_acc")
        factories.create_submission(
            user_id=owner.id, contest_id=contest.id, status="accepted"
        )
        client.post(
            "/api/user/login",
            json={"email": owner.email, "password": "TestPass123!"},
        )
        resp = client.put(
            f"/api/contest/{contest.id}",
            json={
                "scoring_parameters": {
                    "enabled": True,
                    "parameters": [{"name": "Quality", "weight": 100}],
                }
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data.get("locked") is True
        assert "Cannot change scoring system" in data.get("error", "")

    def test_update_contest_blocks_scoring_mode_change_with_rejected_submissions(
        self, client, db, factories
    ):
        owner = factories.create_user(
            username="owner_rej", email="owner_rej@example.com", is_trusted_member=True
        )
        contest = factories.create_contest(created_by="owner_rej")
        factories.create_submission(
            user_id=owner.id, contest_id=contest.id, status="rejected"
        )
        client.post(
            "/api/user/login",
            json={"email": owner.email, "password": "TestPass123!"},
        )
        resp = client.put(
            f"/api/contest/{contest.id}",
            json={
                "scoring_parameters": {
                    "enabled": True,
                    "parameters": [{"name": "Quality", "weight": 100}],
                }
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data.get("locked") is True
        assert "Cannot change scoring system" in data.get("error", "")

    def test_update_contest_allows_scoring_mode_change_with_only_pending(
        self, client, db, factories
    ):
        owner = factories.create_user(
            username="owner_pend",
            email="owner_pend@example.com",
            is_trusted_member=True,
        )
        contest = factories.create_contest(created_by="owner_pend")
        factories.create_submission(
            user_id=owner.id, contest_id=contest.id, status="pending"
        )
        client.post(
            "/api/user/login",
            json={"email": owner.email, "password": "TestPass123!"},
        )
        resp = client.put(
            f"/api/contest/{contest.id}",
            json={
                "scoring_parameters": {
                    "enabled": True,
                    "parameters": [{"name": "Quality", "weight": 100}],
                }
            },
        )
        assert resp.status_code == 200


class TestContestRequestFlow:
    def test_create_contest_request_as_regular_user(self, client, db, factories):
        user = factories.create_user(
            username="req_user", email="req_user@example.com"
        )
        jury = factories.create_user(username="jury_member", email="jury_member@example.com")
        client.post(
            "/api/user/login",
            json={"email": user.email, "password": "TestPass123!"},
        )
        resp = client.post(
            "/api/contest/requests",
            json={
                "name": "Requested Contest",
                "project_name": "TestProject",
                "jury_members": ["jury_member"],
                "min_byte_count": 100,
                "categories": ["https://en.wikipedia.org/wiki/Category:Test"],
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "requestId" in data

    def test_create_contest_request_as_trusted_user_blocked(self, client, db, factories):
        user = factories.create_user(
            username="trusted_req",
            email="trusted_req@example.com",
            is_trusted_member=True,
        )
        jury = factories.create_user(
            username="jury_req", email="jury_req@example.com"
        )
        client.post(
            "/api/user/login",
            json={"email": user.email, "password": "TestPass123!"},
        )
        resp = client.post(
            "/api/contest/requests",
            json={
                "name": "Should Fail",
                "project_name": "TestProject",
                "jury_members": ["jury_req"],
                "min_byte_count": 100,
                "categories": ["https://en.wikipedia.org/wiki/Category:Test"],
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "already have permission" in data.get("error", "")

    def test_approve_contest_request_creates_contest(self, client, db, factories):
        requester = factories.create_user(
            username="req_approve", email="req_approve@example.com"
        )
        jury = factories.create_user(
            username="jury_approve", email="jury_approve@example.com"
        )
        superadmin = factories.create_user(
            username="super_approve",
            email="super_approve@example.com",
            role="superadmin",
        )
        client.post(
            "/api/user/login",
            json={"email": requester.email, "password": "TestPass123!"},
        )
        create_resp = client.post(
            "/api/contest/requests",
            json={
                "name": "Approved Contest",
                "project_name": "TestProject",
                "jury_members": ["jury_approve"],
                "min_byte_count": 100,
                "categories": ["https://en.wikipedia.org/wiki/Category:Test"],
            },
        )
        assert create_resp.status_code == 201
        request_id = create_resp.get_json()["requestId"]

        client.post(
            "/api/user/login",
            json={"email": superadmin.email, "password": "TestPass123!"},
        )
        approve_resp = client.post(
            f"/api/contest/requests/{request_id}/approve"
        )
        assert approve_resp.status_code == 200
        data = approve_resp.get_json()
        assert "contestId" in data
        assert data["contestId"] is not None

    def test_reject_contest_request_updates_status(self, client, db, factories):
        requester = factories.create_user(
            username="req_reject", email="req_reject@example.com"
        )
        jury = factories.create_user(
            username="jury_reject", email="jury_reject@example.com"
        )
        superadmin = factories.create_user(
            username="super_reject",
            email="super_reject@example.com",
            role="superadmin",
        )
        client.post(
            "/api/user/login",
            json={"email": requester.email, "password": "TestPass123!"},
        )
        create_resp = client.post(
            "/api/contest/requests",
            json={
                "name": "Rejected Contest",
                "project_name": "TestProject",
                "jury_members": ["jury_reject"],
                "min_byte_count": 100,
                "categories": ["https://en.wikipedia.org/wiki/Category:Test"],
            },
        )
        assert create_resp.status_code == 201
        request_id = create_resp.get_json()["requestId"]

        client.post(
            "/api/user/login",
            json={"email": superadmin.email, "password": "TestPass123!"},
        )
        reject_resp = client.post(
            f"/api/contest/requests/{request_id}/reject",
            json={"rejection_reason": "Not needed right now"},
        )
        assert reject_resp.status_code == 200
        data = reject_resp.get_json()
        assert data["requestId"] == request_id

    def test_non_superadmin_cannot_approve_request(self, client, db, factories):
        requester = factories.create_user(
            username="req_nonsa", email="req_nonsa@example.com"
        )
        jury = factories.create_user(
            username="jury_nonsa", email="jury_nonsa@example.com"
        )
        regular = factories.create_user(
            username="regular_nonsa", email="regular_nonsa@example.com"
        )
        client.post(
            "/api/user/login",
            json={"email": requester.email, "password": "TestPass123!"},
        )
        create_resp = client.post(
            "/api/contest/requests",
            json={
                "name": "Blocked Contest",
                "project_name": "TestProject",
                "jury_members": ["jury_nonsa"],
                "min_byte_count": 100,
                "categories": ["https://en.wikipedia.org/wiki/Category:Test"],
            },
        )
        assert create_resp.status_code == 201
        request_id = create_resp.get_json()["requestId"]

        client.post(
            "/api/user/login",
            json={"email": regular.email, "password": "TestPass123!"},
        )
        resp = client.post(f"/api/contest/requests/{request_id}/approve")
        assert resp.status_code == 403


class TestCrawlCategory:
    def test_crawl_category_creates_pending_submissions(
        self, client, db, factories, monkeypatch
    ):
        owner = factories.create_user(
            username="crawl_owner",
            email="crawl_owner@example.com",
            is_trusted_member=True,
        )
        jury = factories.create_user(
            username="crawl_jury", email="crawl_jury@example.com"
        )
        automated_settings = {
            "enabled": True,
            "eligibility": {"min_edits": 0, "min_outgoing_links": 0},
            "evaluation": {"points_per_accepted": 10},
        }
        contest = factories.create_contest(
            created_by="crawl_owner",
            jury_members=["crawl_jury"],
            automated_settings=automated_settings,
            categories=["https://en.wikipedia.org/wiki/Category:Test"],
        )

        fake_crawl_result = {
            "articles": [
                {
                    "title": "Crawl Article One",
                    "url": "https://en.wikipedia.org/wiki/Crawl_Article_One",
                    "page_id": "1",
                },
                {
                    "title": "Crawl Article Two",
                    "url": "https://en.wikipedia.org/wiki/Crawl_Article_Two",
                    "page_id": "2",
                },
            ],
            "total": 2,
            "category": "Test",
            "wiki_base": "https://en.wikipedia.org",
            "has_more": False,
            "next_continue": None,
        }

        import app.utils as app_utils
        import app.routes.contest_routes as contest_routes

        monkeypatch.setattr(
            app_utils, "crawl_category_articles", lambda *a, **kw: fake_crawl_result
        )
        monkeypatch.setattr(
            contest_routes, "crawl_category_articles", lambda *a, **kw: fake_crawl_result
        )

        client.post(
            "/api/user/login",
            json={"email": jury.email, "password": "TestPass123!"},
        )
        resp = client.post(
            f"/api/contest/{contest.id}/crawl-category",
            json={
                "category_url": "https://en.wikipedia.org/wiki/Category:Test",
                "limit": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_imported"] == 2
        assert len(data["articles"]) == 2

    def test_crawl_category_skips_duplicates(
        self, client, db, factories, monkeypatch
    ):
        owner = factories.create_user(
            username="dup_owner",
            email="dup_owner@example.com",
            is_trusted_member=True,
        )
        jury = factories.create_user(
            username="dup_jury", email="dup_jury@example.com"
        )
        automated_settings = {
            "enabled": True,
            "eligibility": {"min_edits": 0, "min_outgoing_links": 0},
            "evaluation": {"points_per_accepted": 10},
        }
        contest = factories.create_contest(
            created_by="dup_owner",
            jury_members=["dup_jury"],
            automated_settings=automated_settings,
            categories=["https://en.wikipedia.org/wiki/Category:Test"],
        )
        existing_link = "https://en.wikipedia.org/wiki/Crawl_Article_One"
        factories.create_submission(
            user_id=jury.id, contest_id=contest.id, article_link=existing_link
        )

        fake_crawl_result = {
            "articles": [
                {
                    "title": "Crawl Article One",
                    "url": existing_link,
                    "page_id": "1",
                },
                {
                    "title": "Crawl Article Two",
                    "url": "https://en.wikipedia.org/wiki/Crawl_Article_Two",
                    "page_id": "2",
                },
            ],
            "total": 2,
            "category": "Test",
            "wiki_base": "https://en.wikipedia.org",
            "has_more": False,
            "next_continue": None,
        }

        import app.utils as app_utils
        import app.routes.contest_routes as contest_routes

        monkeypatch.setattr(
            app_utils, "crawl_category_articles", lambda *a, **kw: fake_crawl_result
        )
        monkeypatch.setattr(
            contest_routes, "crawl_category_articles", lambda *a, **kw: fake_crawl_result
        )

        client.post(
            "/api/user/login",
            json={"email": jury.email, "password": "TestPass123!"},
        )
        resp = client.post(
            f"/api/contest/{contest.id}/crawl-category",
            json={
                "category_url": "https://en.wikipedia.org/wiki/Category:Test",
                "limit": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_imported"] == 1
        assert data["skipped"] == 1

    def test_crawl_category_only_for_automated_contests(self, client, db, factories):
        owner = factories.create_user(
            username="auto_check_owner",
            email="auto_check_owner@example.com",
            is_trusted_member=True,
        )
        jury = factories.create_user(
            username="auto_check_jury", email="auto_check_jury@example.com"
        )
        contest = factories.create_contest(
            created_by="auto_check_owner",
            jury_members=["auto_check_jury"],
        )

        client.post(
            "/api/user/login",
            json={"email": jury.email, "password": "TestPass123!"},
        )
        resp = client.post(
            f"/api/contest/{contest.id}/crawl-category",
            json={
                "category_url": "https://en.wikipedia.org/wiki/Category:Test",
                "limit": 10,
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "automated scoring" in data.get("error", "").lower()

    def test_crawl_category_non_jury_blocked(self, client, db, factories, monkeypatch):
        owner = factories.create_user(
            username="blocked_owner",
            email="blocked_owner@example.com",
            is_trusted_member=True,
        )
        jury = factories.create_user(
            username="blocked_jury", email="blocked_jury@example.com"
        )
        outsider = factories.create_user(
            username="blocked_outsider", email="blocked_outsider@example.com"
        )
        automated_settings = {
            "enabled": True,
            "eligibility": {"min_edits": 0, "min_outgoing_links": 0},
            "evaluation": {"points_per_accepted": 10},
        }
        contest = factories.create_contest(
            created_by="blocked_owner",
            jury_members=["blocked_jury"],
            automated_settings=automated_settings,
            categories=["https://en.wikipedia.org/wiki/Category:Test"],
        )

        fake_crawl_result = {
            "articles": [
                {
                    "title": "Blocked Article",
                    "url": "https://en.wikipedia.org/wiki/Blocked_Article",
                    "page_id": "1",
                },
            ],
            "total": 1,
            "category": "Test",
            "wiki_base": "https://en.wikipedia.org",
            "has_more": False,
            "next_continue": None,
        }

        import app.utils as app_utils

        monkeypatch.setattr(
            app_utils, "crawl_category_articles", lambda *a, **kw: fake_crawl_result
        )

        client.post(
            "/api/user/login",
            json={"email": outsider.email, "password": "TestPass123!"},
        )
        resp = client.post(
            f"/api/contest/{contest.id}/crawl-category",
            json={
                "category_url": "https://en.wikipedia.org/wiki/Category:Test",
                "limit": 10,
            },
        )
        assert resp.status_code == 403
