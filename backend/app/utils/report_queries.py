"""
Report Query Functions for WikiContest Application
FIXED: Removed all submission_type references
"""

from sqlalchemy import func, case, distinct
from app.database import db
from app.models.submission import Submission
from app.models.user import User


def get_submission_statistics(contest_id):
    """Aggregate submission statistics for a contest"""
    stats = db.session.query(
        func.count(Submission.id).label('total'),
        func.sum(case((Submission.status == 'accepted', 1), else_=0)).label('accepted'),
        func.sum(case((Submission.status == 'rejected', 1), else_=0)).label('rejected'),
        func.sum(case((Submission.status == 'pending', 1), else_=0)).label('pending'),
        func.sum(Submission.score).label('total_points'),
        func.count(distinct(Submission.user_id)).label('unique_participants')
    ).filter(
        Submission.contest_id == contest_id
    ).first()
    
    return {
        'total_submissions': stats.total or 0,
        'accepted': stats.accepted or 0,
        'rejected': stats.rejected or 0,
        'pending': stats.pending or 0,
        'total_points': stats.total_points or 0,
        'unique_participants': stats.unique_participants or 0
    }


def get_top_contributors(contest_id, limit=None):
    """Get top contributors ranked by total points"""
    query = db.session.query(
        Submission.user_id,
        User.username,
        User.email,
        func.count(Submission.id).label('total_submissions'),
        func.sum(case((Submission.status == 'accepted', 1), else_=0)).label('accepted'),
        func.sum(case((Submission.status == 'rejected', 1), else_=0)).label('rejected'),
        func.sum(case((Submission.status == 'pending', 1), else_=0)).label('pending'),
        func.sum(Submission.score).label('total_points')
    ).join(
        User, Submission.user_id == User.id
    ).filter(
        Submission.contest_id == contest_id
    ).group_by(
        Submission.user_id, User.username, User.email
    ).order_by(
        func.sum(Submission.score).desc()
    )
    
    if limit:
        query = query.limit(limit)
    
    results = query.all()
    
    return [
        {
            'rank': idx + 1,
            'user_id': r.user_id,
            'username': r.username,
            'email': r.email,
            'total_submissions': r.total_submissions,
            'accepted': r.accepted or 0,
            'rejected': r.rejected or 0,
            'pending': r.pending or 0,
            'total_points': r.total_points or 0
        }
        for idx, r in enumerate(results)
    ]


def get_submission_timeline(contest_id):
    """Get submissions grouped by date"""
    results = db.session.query(
        func.date(Submission.submitted_at).label('date'),
        func.count(Submission.id).label('total'),
        func.sum(case((Submission.status == 'accepted', 1), else_=0)).label('accepted'),
        func.sum(case((Submission.status == 'rejected', 1), else_=0)).label('rejected')
    ).filter(
        Submission.contest_id == contest_id
    ).group_by(
        func.date(Submission.submitted_at)
    ).order_by(
        func.date(Submission.submitted_at)
    ).all()
    
    return [
        {
            'date': r.date.isoformat(),
            'total': r.total,
            'accepted': r.accepted or 0,
            'rejected': r.rejected or 0
        }
        for r in results
    ]


def get_submissions_by_type(contest_id):
    """
    REMOVED: submission_type not available yet
    Returns empty list for now
    """
    # Return empty list since submission_type column doesn't exist
    return []


def get_judge_statistics(contest_id):
    """Get statistics for each judge/reviewer"""
    results = db.session.query(
        Submission.reviewed_by,
        User.username,
        func.count(Submission.id).label('total_reviewed'),
        func.sum(case((Submission.status == 'accepted', 1), else_=0)).label('accepted'),
        func.sum(case((Submission.status == 'rejected', 1), else_=0)).label('rejected')
    ).join(
        User, Submission.reviewed_by == User.id
    ).filter(
        Submission.contest_id == contest_id,
        Submission.reviewed_by.isnot(None)
    ).group_by(
        Submission.reviewed_by, User.username
    ).order_by(
        func.count(Submission.id).desc()
    ).all()
    
    return [
        {
            'judge_username': r.username,
            'total_reviewed': r.total_reviewed,
            'accepted': r.accepted or 0,
            'rejected': r.rejected or 0,
            'acceptance_rate': round((r.accepted / r.total_reviewed * 100), 2) if r.total_reviewed > 0 else 0
        }
        for r in results
    ]


def get_all_submissions(contest_id):
    """Get all submissions for contest - FIXED: removed submission_type"""
    submissions = db.session.query(
        Submission,
        User.username
    ).join(
        User, Submission.user_id == User.id
    ).filter(
        Submission.contest_id == contest_id
    ).order_by(
        Submission.score.desc(),
        Submission.submitted_at.desc()
    ).all()

    return [
        {
            'submission_id': submission.id,
            'username': username,
            'article_title': submission.article_title,
            'article_link': submission.article_link,
            'status': submission.status,
            'score': submission.score or 0,
            'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
            'reviewed_at': submission.reviewed_at.isoformat() if submission.reviewed_at else None,
        }
        for submission, username in submissions
    ]