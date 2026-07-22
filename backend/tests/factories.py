"""
Factory helpers for creating test data in WikiEval tests.

Usage in a test:
    def test_something(db, factories):
        user = factories.create_user(role="admin")
        contest = factories.create_contest(created_by=user.username)
        ...
"""

from datetime import date, datetime, timedelta

from app.models.user import User
from app.models.contest import Contest
from app.models.submission import Submission
from app.models.trusted_member_request import TrustedMemberRequest
from app.database import db


def create_user(
    username="testuser",
    email="test@example.com",
    password="TestPass123!",
    role="user",
    is_trusted_member=False,
):
    """
    Create and persist a user with the specified account and trusted-member settings.

    Parameters:
    	username (str): The user's username.
    	email (str): The user's email address.
    	password (str): The user's password.
    	role (str): The user's application role.
    	is_trusted_member (bool): Whether the user is a trusted member.

    Returns:
    	User: The persisted user.
    """
    user = User(
        username=username,
        email=email,
        password=password,
        role=role,
    )
    user.is_trusted_member = is_trusted_member
    user.save()
    return user


def create_contest(
    name="Test Contest",
    project_name="TestProject",
    created_by=None,
    description="A test contest",
    start_date=None,
    end_date=None,
    min_byte_count=0,
    min_reference_count=0,
    marks_setting_accepted=10,
    marks_setting_rejected=0,
    jury_members=None,
    template_link=None,
    categories=None,
    organizers=None,
    scoring_parameters=None,
    automated_settings=None,
    allowed_submission_type="both",
):
    """
    Create and persist a contest with the specified configuration.

    Parameters:
        created_by: ID of the user creating the contest.
            Defaults to creating a default user if None.
        start_date: Contest start date; defaults to yesterday.
        end_date: Contest end date; defaults to seven days from today.
        jury_members: Jury members assigned to the contest (list of usernames).
        categories: Categories associated with the contest.
        organizers: Organizers associated with the contest (list of usernames).
        scoring_parameters: Optional scoring configuration.
        automated_settings: Optional automated-evaluation configuration.
        allowed_submission_type: Types of submissions accepted by the contest.

    Returns:
        The persisted Contest instance.
    """
    if created_by is None:
        default_user = create_user(
            username="default_creator",
            email="default_creator@example.com",
            is_trusted_member=True,
        )
        created_by = default_user.id
    elif isinstance(created_by, str):
        # Legacy support: convert username to user ID
        from app.models.user import User
        user = User.query.filter_by(username=created_by).first()
        if user is None:
            user = create_user(username=created_by, email=f"{created_by}@example.com")
        created_by = user.id
    if start_date is None:
        start_date = date.today() - timedelta(days=1)
    if end_date is None:
        end_date = date.today() + timedelta(days=7)
    if jury_members is None:
        jury_members = []
    if categories is None:
        categories = []
    if organizers is None:
        organizers = []

    contest = Contest(
        name=name,
        project_name=project_name,
        created_by=created_by,
        description=description,
        start_date=start_date,
        end_date=end_date,
        min_byte_count=min_byte_count,
        min_reference_count=min_reference_count,
        marks_setting_accepted=marks_setting_accepted,
        marks_setting_rejected=marks_setting_rejected,
        jury_members=jury_members,
        template_link=template_link,
        categories=categories,
        organizers=organizers,
        allowed_submission_type=allowed_submission_type,
    )
    if scoring_parameters:
        contest.set_scoring_parameters(scoring_parameters)
    if automated_settings:
        contest.set_automated_settings(automated_settings)
    db.session.add(contest)
    db.session.commit()
    return contest


def create_submission(
    user_id,
    contest_id,
    article_title="Test Article",
    article_link="https://en.wikipedia.org/wiki/Test_Article",
    status="pending",
    article_byte_count=5000,
    article_page_id=12345,
):
    """
    Create and persist a submission for a contest participant.

    Parameters:
        user_id: Identifier of the submitting user.
        contest_id: Identifier of the contest.
        article_title: Title of the submitted article.
        article_link: URL of the submitted article.
        status: Initial submission status.
        article_byte_count: Byte count of the submitted article.
        article_page_id: Identifier of the submitted article page.

    Returns:
        The persisted submission.
    """
    submission = Submission(
        user_id=user_id,
        contest_id=contest_id,
        article_title=article_title,
        article_link=article_link,
        status=status,
        article_byte_count=article_byte_count,
        article_page_id=article_page_id,
    )
    db.session.add(submission)
    db.session.commit()
    return submission
