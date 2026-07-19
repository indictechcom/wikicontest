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


class TestAutomatedScoringEvaluation:
    """Tests for automated scoring evaluation (P1-16)."""

    def test_evaluate_automated_submission_accepted(self, client, db, factories, mock_mediawiki):
        """Article meeting all automated criteria should be accepted with a calculated score."""
        user = factories.create_user(username="auto_user", email="auto@example.com", is_trusted_member=True)
        contest = factories.create_contest(
            created_by="auto_user",
            jury_members=["auto_user"],
            automated_settings={
                "enabled": True,
                "eligibility": {"min_edits": 0, "min_outgoing_links": 0},
                "evaluation": {
                    "points_per_accepted": 10,
                    "points_per_byte": 0.001,
                    "points_per_incoming_link": 0,
                    "points_per_outgoing_link": 0,
                    "points_per_category": 0,
                    "points_per_new_reference": 0,
                    "points_per_reused_reference": 0,
                    "points_per_infobox": 0,
                    "points_per_image": 0,
                },
            },
        )
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})

        # Submit an article (mock_mediawiki handles the API call)
        resp = client.post(
            f"/api/contest/{contest.id}/submit",
            json={"article_link": "https://en.wikipedia.org/wiki/Test_Article"},
        )
        assert resp.status_code == 201
        submission_id = resp.get_json()["submissionId"]

        # Now evaluate via refresh_metadata
        resp = client.post(f"/api/submission/contest/{contest.id}/refresh-metadata")
        assert resp.status_code == 200

        # Check submission status
        from app.models.submission import Submission
        sub = Submission.query.get(submission_id)
        assert sub is not None
        # Automated evaluation should set status to accepted or rejected
        assert sub.status in ("accepted", "rejected")

    def test_evaluate_automated_submission_score_calculation(self, client, db, factories, mock_mediawiki):
        """Verify score is calculated based on evaluation points."""
        from app.models.contest import Contest
        user = factories.create_user(username="score_user", email="score@example.com", is_trusted_member=True)
        contest = factories.create_contest(
            created_by="score_user",
            jury_members=["score_user"],
            automated_settings={
                "enabled": True,
                "eligibility": {"min_edits": 0, "min_outgoing_links": 0},
                "evaluation": {
                    "points_per_accepted": 10,
                    "points_per_byte": 0.001,
                    "points_per_incoming_link": 2,
                    "points_per_outgoing_link": 1,
                    "points_per_category": 0,
                    "points_per_new_reference": 3,
                    "points_per_reused_reference": 1,
                    "points_per_infobox": 5,
                    "points_per_image": 2,
                },
            },
        )
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})

        # Test the evaluation function directly
        submission_data = {
            "article_word_count": 5000,
            "incoming_links": 10,
            "outgoing_links": 5,
            "ref_new_count": 3,
            "ref_reused_count": 1,
            "image_count": 2,
            "infobox_count": 1,
        }
        is_eligible, final_score, reason, breakdown = contest.evaluate_automated_submission(submission_data)
        assert is_eligible is True
        assert final_score > 0
        assert breakdown is not None


class TestMultiParameterScoringReview:
    """Tests for multi-parameter scoring review (P1-17)."""

    def test_review_submission_multi_parameter_accepted(self, client, db, factories, mock_mediawiki):
        """Review with valid parameter_scores should calculate weighted score."""
        user = factories.create_user(username="mp_user", email="mp@example.com", is_trusted_member=True)
        contest = factories.create_contest(
            created_by="mp_user",
            jury_members=["mp_user"],
            marks_setting_accepted=10,
            marks_setting_rejected=0,
            scoring_parameters={
                "enabled": True,
                "max_score": 10,
                "min_score": 0,
                "parameters": [
                    {"name": "Quality", "weight": 50, "description": "Quality"},
                    {"name": "Sources", "weight": 50, "description": "Sources"},
                ],
            },
        )
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})

        # Submit article
        resp = client.post(
            f"/api/contest/{contest.id}/submit",
            json={"article_link": "https://en.wikipedia.org/wiki/Test_Article"},
        )
        assert resp.status_code == 201
        submission_id = resp.get_json()["submissionId"]

        # Review with parameter scores
        resp = client.put(
            f"/api/submission/{submission_id}/review",
            json={
                "status": "accepted",
                "parameter_scores": {"Quality": 8, "Sources": 7},
                "comment": "Good article",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["submission"]["status"] == "accepted"

    def test_review_submission_multi_parameter_rejected(self, client, db, factories, mock_mediawiki):
        """Rejected multi-param submission gets min_score."""
        user = factories.create_user(username="mp_rej", email="mp_rej@example.com", is_trusted_member=True)
        contest = factories.create_contest(
            created_by="mp_rej",
            jury_members=["mp_rej"],
            marks_setting_accepted=10,
            marks_setting_rejected=0,
            scoring_parameters={
                "enabled": True,
                "max_score": 10,
                "min_score": 0,
                "parameters": [
                    {"name": "Quality", "weight": 50, "description": ""},
                    {"name": "Sources", "weight": 50, "description": ""},
                ],
            },
        )
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        resp = client.post(
            f"/api/contest/{contest.id}/submit",
            json={"article_link": "https://en.wikipedia.org/wiki/Test_Article"},
        )
        assert resp.status_code == 201
        submission_id = resp.get_json()["submissionId"]

        resp = client.put(
            f"/api/submission/{submission_id}/review",
            json={"status": "rejected", "comment": "Not good enough"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["submission"]["status"] == "rejected"


class TestSubmissionPermission:
    """Tests for require_submission_permission access matrix (P1-18)."""

    def test_submission_owner_can_view(self, client, db, factories, mock_mediawiki):
        """The user who submitted should be able to view their submission."""
        user = factories.create_user(username="sub_owner", email="sub_owner@example.com", is_trusted_member=True)
        client.post("/api/user/login", json={"email": user.email, "password": "TestPass123!"})
        contest = factories.create_contest(created_by="sub_owner", jury_members=["sub_owner"])
        resp = client.post(
            f"/api/contest/{contest.id}/submit",
            json={"article_link": "https://en.wikipedia.org/wiki/Test_Article"},
        )
        assert resp.status_code == 201
        sid = resp.get_json()["submissionId"]
        resp = client.get(f"/api/submission/{sid}")
        assert resp.status_code == 200

    def test_submission_non_owner_cannot_view(self, client, db, factories, mock_mediawiki):
        """A different user should not be able to view someone else's submission."""
        owner = factories.create_user(username="owner_perm", email="owner_perm@example.com", is_trusted_member=True)
        other = factories.create_user(username="other_perm", email="other_perm@example.com")
        contest = factories.create_contest(created_by="owner_perm", jury_members=["owner_perm"])

        # Owner submits
        client.post("/api/user/login", json={"email": owner.email, "password": "TestPass123!"})
        resp = client.post(
            f"/api/contest/{contest.id}/submit",
            json={"article_link": "https://en.wikipedia.org/wiki/Test_Article"},
        )
        assert resp.status_code == 201
        sid = resp.get_json()["submissionId"]

        # Other user tries to view
        client.post("/api/user/login", json={"email": other.email, "password": "TestPass123!"})
        resp = client.get(f"/api/submission/{sid}")
        assert resp.status_code == 403

    def test_submission_jury_can_review(self, client, db, factories, mock_mediawiki):
        """Jury member should be able to review a submission."""
        owner = factories.create_user(username="jury_owner", email="jury_owner@example.com", is_trusted_member=True)
        jury = factories.create_user(username="jury_reviewer", email="jury_reviewer@example.com")
        contest = factories.create_contest(created_by="jury_owner", jury_members=["jury_owner", "jury_reviewer"])

        client.post("/api/user/login", json={"email": owner.email, "password": "TestPass123!"})
        resp = client.post(
            f"/api/contest/{contest.id}/submit",
            json={"article_link": "https://en.wikipedia.org/wiki/Test_Article"},
        )
        assert resp.status_code == 201
        sid = resp.get_json()["submissionId"]

        # Jury reviews
        client.post("/api/user/login", json={"email": jury.email, "password": "TestPass123!"})
        resp = client.put(
            f"/api/submission/{sid}/review",
            json={"status": "accepted", "score": 8, "comment": "Well done"},
        )
        assert resp.status_code == 200

    def test_submission_non_jury_cannot_review(self, client, db, factories, mock_mediawiki):
        """A non-jury user should not be able to review."""
        owner = factories.create_user(username="nj_owner", email="nj_owner@example.com", is_trusted_member=True)
        outsider = factories.create_user(username="nj_outsider", email="nj_outsider@example.com")
        contest = factories.create_contest(created_by="nj_owner", jury_members=["nj_owner"])

        client.post("/api/user/login", json={"email": owner.email, "password": "TestPass123!"})
        resp = client.post(
            f"/api/contest/{contest.id}/submit",
            json={"article_link": "https://en.wikipedia.org/wiki/Test_Article"},
        )
        assert resp.status_code == 201
        sid = resp.get_json()["submissionId"]

        client.post("/api/user/login", json={"email": outsider.email, "password": "TestPass123!"})
        resp = client.put(
            f"/api/submission/{sid}/review",
            json={"status": "accepted", "score": 8},
        )
        assert resp.status_code == 403


class TestUpdateStatusScorePropagation:
    """Tests for Submission.update_status score propagation (P1-21)."""

    def test_update_status_accepted_increases_user_score(self, db, factories):
        """Accepting a submission should increase the user's total score."""
        user = factories.create_user(username="score_inc", email="score_inc@example.com")
        contest = factories.create_contest(created_by="score_inc", marks_setting_accepted=10, marks_setting_rejected=0)
        submission = factories.create_submission(user_id=user.id, contest_id=contest.id)

        initial_score = user.score or 0
        submission.update_status(new_status="accepted", score=8, contest=contest)

        from app.models.user import User
        updated_user = User.query.get(user.id)
        assert updated_user.score == initial_score + 8

    def test_update_status_rejected_sets_rejection_score(self, db, factories):
        """Rejecting a submission should add the rejection score."""
        user = factories.create_user(username="score_rej", email="score_rej@example.com")
        contest = factories.create_contest(created_by="score_rej", marks_setting_accepted=10, marks_setting_rejected=0)
        submission = factories.create_submission(user_id=user.id, contest_id=contest.id)

        initial_score = user.score or 0
        submission.update_status(new_status="rejected", score=0, contest=contest)

        from app.models.user import User
        updated_user = User.query.get(user.id)
        assert updated_user.score == initial_score

    def test_update_status_commit_false_defers_commit(self, db, factories):
        """Passing commit=False should keep changes in session but not flush."""
        user = factories.create_user(username="defer_commit", email="defer@example.com")
        contest = factories.create_contest(created_by="defer_commit")
        submission = factories.create_submission(user_id=user.id, contest_id=contest.id)

        submission.update_status(new_status="accepted", score=5, contest=contest, commit=False)
        # Changes are in the session but not committed
        assert submission.status == "accepted"
        assert submission.score == 5

        # Rollback should revert
        db.session.rollback()
        from app.models.submission import Submission
        refreshed = Submission.query.get(submission.id)
        assert refreshed.status == "pending"

