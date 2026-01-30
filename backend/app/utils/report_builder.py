"""
Report Builder for WikiContest Application
COMPLETE VERSION: Comprehensive CSV and PDF reports
FIXED: Handles missing Contest attributes gracefully
"""

import os
import io
from datetime import datetime
from collections import defaultdict
from app.utils.report_queries import (
    get_submission_statistics,
    get_top_contributors,
    get_submission_timeline,
    get_judge_statistics,
    get_all_submissions
)


class CSVReportBuilder:
    """Build ultra-comprehensive CSV reports with ALL contest and submission details"""
    
    def __init__(self, contest, metadata=None):
        self.contest = contest
        self.metadata = metadata or {}
    
    def _safe_get(self, attr, default='N/A'):
        """Safely get contest attribute with fallback"""
        return getattr(self.contest, attr, default)
    
    def generate(self):
        """Generate comprehensive CSV report with all insights"""
        
        # Fetch all data
        stats = get_submission_statistics(self.contest.id)
        top_n = self.metadata.get('top_n', 100)
        top_contributors = get_top_contributors(self.contest.id, limit=top_n)
        timeline = get_submission_timeline(self.contest.id)
        judges = get_judge_statistics(self.contest.id)
        
        output = io.StringIO()
        
        # =====================================================================
        # SECTION 1: REPORT HEADER & METADATA
        # =====================================================================
        output.write("=" * 150 + "\n")
        output.write(f"ULTRA-COMPREHENSIVE CONTEST REPORT - {self.contest.name.upper()}\n")
        output.write("=" * 150 + "\n")
        output.write(f"Generated At:,{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        output.write(f"Report Type:,Complete Contest Analysis with All Insights\n")
        output.write(f"Report Version:,2.0 - Enhanced Edition\n")
        output.write("=" * 150 + "\n\n")
        
        # =====================================================================
        # SECTION 2: CONTEST CONFIGURATION & SETUP
        # =====================================================================
        output.write("-" * 150 + "\n")
        output.write("CONTEST CONFIGURATION & SETUP\n")
        output.write("-" * 150 + "\n\n")
        
        output.write("Field,Value\n")
        output.write(f"Contest ID,{self.contest.id}\n")
        output.write(f"Contest Name,\"{self.contest.name}\"\n")
        output.write(f"Project Name,\"{self._safe_get('project_name', 'N/A')}\"\n")
        
        # Status - calculate if not available
        status = self._safe_get('status', None)
        if not status:
            # Calculate status based on dates
            now = datetime.now()
            try:
                start = datetime.fromisoformat(str(self.contest.start_date)) if self.contest.start_date else None
                end = datetime.fromisoformat(str(self.contest.end_date)) if self.contest.end_date else None
                
                if start and end:
                    if now < start:
                        status = "Upcoming"
                    elif now > end:
                        status = "Past"
                    else:
                        status = "Current"
                else:
                    status = "Unknown"
            except:
                status = "Unknown"
        
        output.write(f"Contest Status,{status}\n")
        output.write(f"Created By,{self._safe_get('created_by', 'Unknown')}\n")
        output.write(f"Created At,{self._safe_get('created_at', 'N/A')}\n")
        output.write(f"Start Date,{self._safe_get('start_date', 'N/A')}\n")
        output.write(f"End Date,{self._safe_get('end_date', 'N/A')}\n")
        
        # Contest duration calculation
        if self.contest.start_date and self.contest.end_date:
            try:
                start = datetime.fromisoformat(str(self.contest.start_date))
                end = datetime.fromisoformat(str(self.contest.end_date))
                duration = (end - start).days
                output.write(f"Contest Duration (Days),{duration}\n")
            except:
                pass
        
        # Description
        description = self._safe_get('description', None)
        if description:
            description_cleaned = str(description).replace('\n', ' ').replace('"', '""')
            output.write(f"Description,\"{description_cleaned}\"\n")
        
        output.write("\n")
        
        # =====================================================================
        # SECTION 3: SUBMISSION RULES & REQUIREMENTS
        # =====================================================================
        output.write("-" * 150 + "\n")
        output.write("SUBMISSION RULES & REQUIREMENTS\n")
        output.write("-" * 150 + "\n\n")
        
        output.write("Rule Type,Value\n")
        
        # Submission type
        submission_type_map = {
            'new': 'New Articles Only',
            'expansion': 'Improved Articles Only',
            'both': 'Both (New + Improved)'
        }
        allowed_type = submission_type_map.get(
            self._safe_get('allowed_submission_type', 'both'),
            self._safe_get('allowed_submission_type', 'both')
        )
        output.write(f"Allowed Submission Type,{allowed_type}\n")
        
        # Minimum requirements
        output.write(f"Minimum Byte Count,{self._safe_get('min_byte_count', 0)}\n")
        output.write(f"Minimum References Required,{self._safe_get('min_reference_count', 0)}\n")
        
        # Categories
        categories = self._safe_get('categories', None)
        if categories:
            categories_list = ', '.join(categories) if isinstance(categories, list) else str(categories)
            output.write(f"Required Categories,\"{categories_list}\"\n")
            output.write(f"Number of Categories,{len(categories) if isinstance(categories, list) else 1}\n")
        
        # Template
        template_link = self._safe_get('template_link', None)
        if template_link:
            output.write(f"Contest Template,\"{template_link}\"\n")
        
        # Contest rules
        rules = self._safe_get('rules', None)
        if rules:
            if isinstance(rules, dict) and 'text' in rules:
                rules_text = str(rules['text']).replace('\n', ' ').replace('"', '""')
            else:
                rules_text = str(rules).replace('\n', ' ').replace('"', '""')
            output.write(f"Contest Rules,\"{rules_text}\"\n")
        
        output.write("\n")
        
        # =====================================================================
        # SECTION 4: SCORING SYSTEM CONFIGURATION
        # =====================================================================
        output.write("-" * 150 + "\n")
        output.write("SCORING SYSTEM CONFIGURATION\n")
        output.write("-" * 150 + "\n\n")
        
        scoring_params = self._safe_get('scoring_parameters', None)
        if scoring_params and isinstance(scoring_params, dict):
            if scoring_params.get('enabled'):
                output.write("Scoring Mode,Multi-Parameter Scoring\n")
                output.write(f"Maximum Score (Accepted),{scoring_params.get('max_score', 10)}\n")
                output.write(f"Minimum Score (Rejected),{scoring_params.get('min_score', 0)}\n")
                output.write("\n")
                
                # Scoring parameters breakdown
                if 'parameters' in scoring_params:
                    output.write("Scoring Parameter,Weight (%),Description\n")
                    for param in scoring_params['parameters']:
                        param_name = param.get('name', 'Unknown')
                        param_weight = param.get('weight', 0)
                        param_desc = param.get('description', 'No description')
                        output.write(f"\"{param_name}\",{param_weight},\"{param_desc}\"\n")
            else:
                output.write("Scoring Mode,Simple Accept/Reject\n")
                output.write(f"Points for Accepted,{self._safe_get('marks_setting_accepted', 0)}\n")
                output.write(f"Points for Rejected,{self._safe_get('marks_setting_rejected', 0)}\n")
        else:
            output.write("Scoring Mode,Simple Accept/Reject\n")
            output.write(f"Points for Accepted,{self._safe_get('marks_setting_accepted', 0)}\n")
            output.write(f"Points for Rejected,{self._safe_get('marks_setting_rejected', 0)}\n")
        
        output.write("\n")
        
        # =====================================================================
        # SECTION 5: TEAM & ORGANIZERS
        # =====================================================================
        output.write("-" * 150 + "\n")
        output.write("CONTEST TEAM & ORGANIZERS\n")
        output.write("-" * 150 + "\n\n")
        
        output.write("Role,Members,Count\n")
        
        # Organizers
        organizers = self._safe_get('organizers', None)
        if organizers:
            organizers_list = ', '.join(organizers) if isinstance(organizers, list) else str(organizers)
            organizers_count = len(organizers) if isinstance(organizers, list) else 1
            output.write(f"Organizers,\"{organizers_list}\",{organizers_count}\n")
        
        # Jury members
        jury = self._safe_get('jury_members', None)
        if jury:
            jury_list = ', '.join(jury) if isinstance(jury, list) else str(jury)
            jury_count = len(jury) if isinstance(jury, list) else 1
            output.write(f"Jury Members,\"{jury_list}\",{jury_count}\n")
        
        output.write("\n")
        
        # =====================================================================
        # SECTION 6: EXECUTIVE SUMMARY & KEY METRICS
        # =====================================================================
        output.write("-" * 150 + "\n")
        output.write("EXECUTIVE SUMMARY & KEY METRICS\n")
        output.write("-" * 150 + "\n\n")
        
        output.write("Metric,Value,Percentage\n")
        output.write(f"Total Submissions,{stats['total_submissions']},100.00%\n")
        output.write(f"Accepted Submissions,{stats['accepted']},{round((stats['accepted'] / stats['total_submissions'] * 100) if stats['total_submissions'] > 0 else 0, 2)}%\n")
        output.write(f"Rejected Submissions,{stats['rejected']},{round((stats['rejected'] / stats['total_submissions'] * 100) if stats['total_submissions'] > 0 else 0, 2)}%\n")
        output.write(f"Pending Review,{stats['pending']},{round((stats['pending'] / stats['total_submissions'] * 100) if stats['total_submissions'] > 0 else 0, 2)}%\n")
        output.write(f"Total Points Awarded,{stats['total_points']},N/A\n")
        output.write(f"Unique Participants,{stats['unique_participants']},N/A\n")
        
        # Additional metrics
        if stats['unique_participants'] > 0:
            avg_submissions = round(stats['total_submissions'] / stats['unique_participants'], 2)
            output.write(f"Average Submissions per Participant,{avg_submissions},N/A\n")
        
        if stats['accepted'] > 0:
            avg_points_per_accepted = round(stats['total_points'] / stats['accepted'], 2)
            output.write(f"Average Points per Accepted Article,{avg_points_per_accepted},N/A\n")
        
        output.write("\n")
        
        # =====================================================================
        # SECTION 7: JUDGE PERFORMANCE ANALYSIS
        # =====================================================================
        if judges:
            output.write("-" * 150 + "\n")
            output.write("JUDGE PERFORMANCE ANALYSIS\n")
            output.write("-" * 150 + "\n\n")
            
            output.write("Judge Username,Total Reviewed,Accepted,Rejected,Pending,Acceptance Rate (%),Rejection Rate (%)\n")
            
            for judge in judges:
                pending = stats['total_submissions'] - judge['total_reviewed']
                rejection_rate = round(100 - judge['acceptance_rate'], 2)
                
                output.write(
                    f"\"{judge['judge_username']}\","
                    f"{judge['total_reviewed']},"
                    f"{judge['accepted']},"
                    f"{judge['rejected']},"
                    f"{pending},"
                    f"{judge['acceptance_rate']},"
                    f"{rejection_rate}\n"
                )
            
            output.write("\n")
        
        # =====================================================================
        # SECTION 8: TOP CONTRIBUTORS LEADERBOARD
        # =====================================================================
        output.write("-" * 150 + "\n")
        output.write(f"TOP {len(top_contributors)} CONTRIBUTORS LEADERBOARD\n")
        output.write("-" * 150 + "\n\n")
        
        output.write("Rank,Username,Email,Total Submissions,Accepted,Rejected,Pending,Total Points,Acceptance Rate (%),Avg Points per Submission\n")
        
        for contrib in top_contributors:
            if contrib['total_submissions'] > 0:
                user_acceptance = round((contrib['accepted'] / contrib['total_submissions']) * 100, 2)
                avg_points = round(contrib['total_points'] / contrib['total_submissions'], 2)
            else:
                user_acceptance = 0
                avg_points = 0
            
            output.write(
                f"{contrib['rank']},"
                f"\"{contrib['username']}\","
                f"\"{contrib['email']}\","
                f"{contrib['total_submissions']},"
                f"{contrib['accepted']},"
                f"{contrib['rejected']},"
                f"{contrib['pending']},"
                f"{contrib['total_points']},"
                f"{user_acceptance},"
                f"{avg_points}\n"
            )
        output.write("\n")
        
        # =====================================================================
        # SECTION 9: DAILY SUBMISSION TIMELINE
        # =====================================================================
        if timeline:
            output.write("-" * 150 + "\n")
            output.write("DAILY SUBMISSION TIMELINE\n")
            output.write("-" * 150 + "\n\n")
            
            output.write("Date,Total Submissions,Accepted,Rejected,Pending,Acceptance Rate (%),Daily Trend,Cumulative Total\n")
            
            cumulative = 0
            for idx, day in enumerate(timeline):
                total = day['total']
                accepted = day['accepted']
                rejected = day['rejected']
                pending = total - accepted - rejected
                
                daily_acceptance = round((accepted / total) * 100, 2) if total > 0 else 0
                
                # Calculate trend
                if idx > 0:
                    prev_total = timeline[idx-1]['total']
                    trend = "↑ Increasing" if total > prev_total else "↓ Decreasing" if total < prev_total else "→ Stable"
                else:
                    trend = "First Day"
                
                cumulative += total
                
                output.write(
                    f"{day['date']},"
                    f"{total},"
                    f"{accepted},"
                    f"{rejected},"
                    f"{pending},"
                    f"{daily_acceptance},"
                    f"\"{trend}\","
                    f"{cumulative}\n"
                )
            output.write("\n")
        
        # =====================================================================
        # SECTION 10: COMPLETE SUBMISSIONS DATABASE (ALL DETAILS)
        # =====================================================================
        output.write("-" * 150 + "\n")
        output.write("COMPLETE SUBMISSIONS DATABASE - ALL ARTICLE DETAILS\n")
        output.write("-" * 150 + "\n\n")
        
        # Enhanced header with ALL fields
        output.write(
            "Submission ID,"
            "Participant Username,"
            "Participant Email,"
            "Article Title,"
            "Article URL,"
            "Original Article Author,"
            "Latest Revision Author,"
            "Total Bytes,"
            "Original Bytes,"
            "Expansion Bytes,"
            "Expansion Type,"
            "Reference Count,"
            "Meets Min References,"
            "Meets Min Bytes,"
            "Article Created Date,"
            "Latest Revision Date,"
            "Status,"
            "Score,"
            "Submitted Date,"
            "Reviewed Date,"
            "Reviewed By,"
            "Days to Review,"
            "Review Comments\n"
        )
        
        # Fetch enhanced submission data
        from app.models.submission import Submission
        from app.models.user import User
        
        submissions_query = Submission.query.filter_by(
            contest_id=self.contest.id
        ).order_by(
            Submission.score.desc(),
            Submission.submitted_at.desc()
        ).all()
        
        for sub in submissions_query:
            # Get participant details
            participant = User.query.get(sub.user_id)
            participant_name = participant.username if participant else 'Unknown'
            participant_email = participant.email if participant else 'N/A'
            
            # Get reviewer details
            reviewer_name = 'Not Reviewed'
            if sub.reviewed_by:
                reviewer = User.query.get(sub.reviewed_by)
                reviewer_name = reviewer.username if reviewer else f'User {sub.reviewed_by}'
            
            # Calculate byte counts
            original_bytes = sub.article_word_count or 0
            expansion_bytes = sub.article_expansion_bytes or 0
            total_bytes = original_bytes + expansion_bytes
            
            # Determine expansion type
            if expansion_bytes > 0:
                expansion_type = "Added Content"
            elif expansion_bytes < 0:
                expansion_type = "Removed Content"
            else:
                expansion_type = "No Change"
            
            # Reference count
            ref_count = sub.article_reference_count or 0
            min_refs = self._safe_get('min_reference_count', 0)
            min_bytes = self._safe_get('min_byte_count', 0)
            meets_min_refs = "Yes" if ref_count >= min_refs else "No"
            meets_min_bytes = "Yes" if total_bytes >= min_bytes else "No"
            
            # Format dates
            article_created = sub.article_created_at.isoformat() if sub.article_created_at else 'N/A'
            latest_revision = sub.latest_revision_timestamp.isoformat() if sub.latest_revision_timestamp else 'N/A'
            submitted = sub.submitted_at.isoformat() if sub.submitted_at else 'N/A'
            reviewed = sub.reviewed_at.isoformat() if sub.reviewed_at else 'Not Reviewed'
            
            # Calculate days to review
            days_to_review = 'N/A'
            if sub.submitted_at and sub.reviewed_at:
                delta = sub.reviewed_at - sub.submitted_at
                days_to_review = delta.days
            
            # Review comments
            review_comments = (sub.review_comment or '').replace('"', '""').replace('\n', ' ') if sub.review_comment else 'No comments'
            
            output.write(
                f"{sub.id},"
                f"\"{participant_name}\","
                f"\"{participant_email}\","
                f"\"{sub.article_title}\","
                f"\"{sub.article_link}\","
                f"\"{sub.article_author or 'Unknown'}\","
                f"\"{sub.latest_revision_author or 'N/A'}\","
                f"{total_bytes},"
                f"{original_bytes},"
                f"{expansion_bytes},"
                f"\"{expansion_type}\","
                f"{ref_count},"
                f"{meets_min_refs},"
                f"{meets_min_bytes},"
                f"{article_created},"
                f"{latest_revision},"
                f"{sub.status},"
                f"{sub.score or 0},"
                f"{submitted},"
                f"{reviewed},"
                f"\"{reviewer_name}\","
                f"{days_to_review},"
                f"\"{review_comments}\"\n"
            )
        
        output.write("\n")
        
        # =====================================================================
        # SECTION 11: PARTICIPANT-WISE DETAILED BREAKDOWN
        # =====================================================================
        output.write("-" * 150 + "\n")
        output.write("PARTICIPANT-WISE DETAILED BREAKDOWN\n")
        output.write("-" * 150 + "\n\n")
        
        output.write(
            "Username,"
            "Email,"
            "Total Articles,"
            "Accepted,"
            "Rejected,"
            "Pending,"
            "Total Bytes,"
            "Avg Bytes,"
            "Total References,"
            "Avg References,"
            "Total Points,"
            "Avg Score,"
            "Highest Score,"
            "Lowest Score,"
            "Success Rate (%),First Submission,Last Submission,Active Days\n"
        )
        
        # Group submissions by user
        from app.models.user import User
        user_stats = defaultdict(lambda: {
            'email': '',
            'total': 0,
            'accepted': 0,
            'rejected': 0,
            'pending': 0,
            'total_bytes': 0,
            'total_refs': 0,
            'total_points': 0,
            'scores': [],
            'submission_dates': []
        })
        
        for sub in submissions_query:
            participant = User.query.get(sub.user_id)
            username = participant.username if participant else 'Unknown'
            email = participant.email if participant else 'N/A'
            
            user_stats[username]['email'] = email
            user_stats[username]['total'] += 1
            
            if sub.status == 'accepted':
                user_stats[username]['accepted'] += 1
            elif sub.status == 'rejected':
                user_stats[username]['rejected'] += 1
            else:
                user_stats[username]['pending'] += 1
            
            # Calculate bytes
            total_bytes = (sub.article_word_count or 0) + (sub.article_expansion_bytes or 0)
            user_stats[username]['total_bytes'] += total_bytes
            
            # References
            user_stats[username]['total_refs'] += (sub.article_reference_count or 0)
            
            # Points and scores
            score = sub.score or 0
            user_stats[username]['total_points'] += score
            user_stats[username]['scores'].append(score)
            
            # Submission dates
            if sub.submitted_at:
                user_stats[username]['submission_dates'].append(sub.submitted_at)
        
        # Write participant summary
        for username in sorted(user_stats.keys()):
            stats_data = user_stats[username]
            total = stats_data['total']
            
            avg_bytes = round(stats_data['total_bytes'] / total, 2) if total > 0 else 0
            avg_refs = round(stats_data['total_refs'] / total, 2) if total > 0 else 0
            avg_score = round(stats_data['total_points'] / total, 2) if total > 0 else 0
            success_rate = round((stats_data['accepted'] / total) * 100, 2) if total > 0 else 0
            
            highest_score = max(stats_data['scores']) if stats_data['scores'] else 0
            lowest_score = min(stats_data['scores']) if stats_data['scores'] else 0
            
            # Date range
            if stats_data['submission_dates']:
                first_date = min(stats_data['submission_dates']).isoformat()
                last_date = max(stats_data['submission_dates']).isoformat()
                active_days = (max(stats_data['submission_dates']) - min(stats_data['submission_dates'])).days + 1
            else:
                first_date = 'N/A'
                last_date = 'N/A'
                active_days = 0
            
            output.write(
                f"\"{username}\","
                f"\"{stats_data['email']}\","
                f"{total},"
                f"{stats_data['accepted']},"
                f"{stats_data['rejected']},"
                f"{stats_data['pending']},"
                f"{stats_data['total_bytes']},"
                f"{avg_bytes},"
                f"{stats_data['total_refs']},"
                f"{avg_refs},"
                f"{stats_data['total_points']},"
                f"{avg_score},"
                f"{highest_score},"
                f"{lowest_score},"
                f"{success_rate},"
                f"{first_date},"
                f"{last_date},"
                f"{active_days}\n"
            )
        
        output.write("\n")
        
        # =====================================================================
        # SECTION 12: ARTICLE INSIGHTS & ANALYTICS
        # =====================================================================
        if submissions_query:
            output.write("-" * 150 + "\n")
            output.write("ARTICLE INSIGHTS & ANALYTICS\n")
            output.write("-" * 150 + "\n\n")
            
            # Calculate insights
            total_bytes_all = sum((s.article_word_count or 0) + (s.article_expansion_bytes or 0) for s in submissions_query)
            total_refs_all = sum(s.article_reference_count or 0 for s in submissions_query)
            
            expansion_added = sum(s.article_expansion_bytes for s in submissions_query if s.article_expansion_bytes and s.article_expansion_bytes > 0)
            expansion_removed = sum(abs(s.article_expansion_bytes) for s in submissions_query if s.article_expansion_bytes and s.article_expansion_bytes < 0)
            
            output.write("Insight Category,Value\n")
            output.write(f"Total Bytes Contributed,{total_bytes_all}\n")
            output.write(f"Total References Added,{total_refs_all}\n")
            output.write(f"Average Bytes per Article,{round(total_bytes_all / len(submissions_query), 2)}\n")
            output.write(f"Average References per Article,{round(total_refs_all / len(submissions_query), 2)}\n")
            output.write(f"Total Content Expansion,{expansion_added}\n")
            output.write(f"Total Content Reduction,{expansion_removed}\n")
            output.write(f"Net Content Change,{expansion_added - expansion_removed}\n")
            
            # Top articles
            max_bytes_article = max(submissions_query, key=lambda s: (s.article_word_count or 0) + (s.article_expansion_bytes or 0))
            output.write(f"Largest Article,\"{max_bytes_article.article_title}\" ({(max_bytes_article.article_word_count or 0) + (max_bytes_article.article_expansion_bytes or 0)} bytes)\n")
            
            max_refs_article = max(submissions_query, key=lambda s: s.article_reference_count or 0)
            output.write(f"Most Referenced Article,\"{max_refs_article.article_title}\" ({max_refs_article.article_reference_count or 0} refs)\n")
            
            max_score_article = max(submissions_query, key=lambda s: s.score or 0)
            output.write(f"Highest Scoring Article,\"{max_score_article.article_title}\" ({max_score_article.score or 0} points)\n")
            
            output.write("\n")
        
        # =====================================================================
        # SECTION 13: COMPLIANCE & QUALITY METRICS
        # =====================================================================
        if submissions_query:
            output.write("-" * 150 + "\n")
            output.write("COMPLIANCE & QUALITY METRICS\n")
            output.write("-" * 150 + "\n\n")
            
            min_bytes = self._safe_get('min_byte_count', 0)
            min_refs = self._safe_get('min_reference_count', 0)
            
            meets_byte_req = sum(1 for s in submissions_query if ((s.article_word_count or 0) + (s.article_expansion_bytes or 0)) >= min_bytes)
            meets_ref_req = sum(1 for s in submissions_query if (s.article_reference_count or 0) >= min_refs)
            meets_both = sum(1 for s in submissions_query if 
                            ((s.article_word_count or 0) + (s.article_expansion_bytes or 0)) >= min_bytes and
                            (s.article_reference_count or 0) >= min_refs)
            
            output.write("Compliance Metric,Count,Percentage\n")
            output.write(f"Meets Byte Requirement ({min_bytes}),{meets_byte_req},{round(meets_byte_req / len(submissions_query) * 100, 2)}%\n")
            output.write(f"Meets Reference Requirement ({min_refs}),{meets_ref_req},{round(meets_ref_req / len(submissions_query) * 100, 2)}%\n")
            output.write(f"Meets Both Requirements,{meets_both},{round(meets_both / len(submissions_query) * 100, 2)}%\n")
            output.write(f"Fails Requirements,{len(submissions_query) - meets_both},{round((len(submissions_query) - meets_both) / len(submissions_query) * 100, 2)}%\n")
            
            output.write("\n")
        
        # =====================================================================
        # SECTION 14: REPORT FOOTER
        # =====================================================================
        output.write("=" * 150 + "\n")
        output.write("END OF COMPREHENSIVE REPORT\n")
        output.write("=" * 150 + "\n")
        output.write(f"Total Submissions,{len(submissions_query)}\n")
        output.write(f"Total Participants,{stats['unique_participants']}\n")
        output.write(f"Total Judges,{len(judges) if judges else 0}\n")
        output.write(f"Generated,{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        output.write(f"Platform,WikiContest v2.0\n")
        output.write("=" * 150 + "\n")
        
        # Save file
        file_path = self._save_file(output.getvalue(), 'csv')
        return file_path
    
    def _save_file(self, content, extension):
        """Save CSV file to reports directory"""
        
        if os.path.exists('/data/project'):
            reports_dir = '/data/project/wikicontest/reports'
        else:
            reports_dir = os.path.join(os.path.dirname(__file__), '../../reports')
        
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = int(datetime.now().timestamp())
        filename = f"contest_{self.contest.id}_report_{timestamp}.{extension}"
        file_path = os.path.join(reports_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f" Comprehensive Report saved: {file_path}")
        
        return file_path


class PDFReportBuilder:
    """Build comprehensive PDF reports with all contest details"""

    def __init__(self, contest, metadata=None):
        self.contest = contest
        self.metadata = metadata or {}
    
    def _safe_get(self, attr, default='N/A'):
        """Safely get contest attribute with fallback"""
        return getattr(self.contest, attr, default)

    def generate(self):
        """Generate comprehensive PDF report"""
        try:
            from reportlab.lib.pagesizes import A4, letter
            from reportlab.platypus import (
                SimpleDocTemplate,
                Table,
                TableStyle,
                Paragraph,
                Spacer,
                PageBreak,
                Image,
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
        except ImportError:
            raise ImportError("reportlab is required for PDF generation")

        # Fetch data
        stats = get_submission_statistics(self.contest.id)
        top_n = self.metadata.get("top_n", 20)
        top_contributors = get_top_contributors(self.contest.id, limit=top_n)
        timeline = get_submission_timeline(self.contest.id)
        judges = get_judge_statistics(self.contest.id)

        file_path = self._get_file_path("pdf")
        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            title=f"{self.contest.name} - Comprehensive Contest Report",
            author="WikiContest Platform",
            subject=f"Contest Report - {datetime.now().strftime('%Y-%m-%d')}",
        )
        
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#006699"),
            spaceAfter=30,
            alignment=1,
            fontName="Helvetica-Bold"
        )
        
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=16,
            textColor=colors.HexColor("#006699"),
            spaceAfter=12,
            spaceBefore=12,
            fontName="Helvetica-Bold"
        )

        # =====================================================================
        # TITLE PAGE
        # =====================================================================
        story.append(Spacer(1, 1 * inch))
        story.append(Paragraph(f"COMPREHENSIVE CONTEST REPORT", title_style))
        story.append(Paragraph(f"{self.contest.name}", title_style))
        story.append(Spacer(1, 0.5 * inch))
        
        # Calculate status
        status = self._safe_get('status', 'Unknown')
        if status == 'Unknown':
            try:
                now = datetime.now()
                start = datetime.fromisoformat(str(self.contest.start_date)) if self.contest.start_date else None
                end = datetime.fromisoformat(str(self.contest.end_date)) if self.contest.end_date else None
                if start and end:
                    status = "Upcoming" if now < start else "Past" if now > end else "Current"
            except:
                pass
        
        story.append(Paragraph(f"<b>Status:</b> {status}", styles["Normal"]))
        story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}", styles["Normal"]))
        story.append(Paragraph(f"<b>Contest ID:</b> {self.contest.id}", styles["Normal"]))
        story.append(PageBreak())

        # =====================================================================
        # CONTEST INFORMATION
        # =====================================================================
        story.append(Paragraph("Contest Information", heading_style))
        
        contest_info = [
            ["Field", "Value"],
            ["Contest Name", self.contest.name],
            ["Project", self._safe_get('project_name', 'N/A')],
            ["Created By", self._safe_get('created_by', 'Unknown')],
            ["Start Date", str(self._safe_get('start_date', 'N/A'))],
            ["End Date", str(self._safe_get('end_date', 'N/A'))],
        ]
        
        # Add duration if available
        if self.contest.start_date and self.contest.end_date:
            try:
                start = datetime.fromisoformat(str(self.contest.start_date))
                end = datetime.fromisoformat(str(self.contest.end_date))
                duration = (end - start).days
                contest_info.append(["Duration", f"{duration} days"])
            except:
                pass
        
        info_table = Table(contest_info, colWidths=[2.5 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#006699")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3 * inch))

        # =====================================================================
        # SCORING SYSTEM
        # =====================================================================
        story.append(Paragraph("Scoring System", heading_style))
        
        scoring_params = self._safe_get('scoring_parameters', None)
        if scoring_params and isinstance(scoring_params, dict) and scoring_params.get('enabled'):
            story.append(Paragraph(f"<b>Scoring Mode:</b> Multi-Parameter Scoring", styles["Normal"]))
            story.append(Paragraph(f"<b>Maximum Score:</b> {scoring_params.get('max_score', 10)}", styles["Normal"]))
            story.append(Paragraph(f"<b>Minimum Score:</b> {scoring_params.get('min_score', 0)}", styles["Normal"]))
            story.append(Spacer(1, 0.2 * inch))
            
            if 'parameters' in scoring_params:
                param_data = [["Parameter", "Weight (%)", "Description"]]
                for param in scoring_params['parameters']:
                    param_data.append([
                        param.get('name', 'Unknown'),
                        str(param.get('weight', 0)),
                        param.get('description', 'No description')
                    ])
                
                param_table = Table(param_data, colWidths=[2 * inch, 1 * inch, 3.5 * inch])
                param_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#006699")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                story.append(param_table)
        else:
            story.append(Paragraph(f"<b>Scoring Mode:</b> Simple Accept/Reject", styles["Normal"]))
            story.append(Paragraph(f"<b>Points for Accepted:</b> {self._safe_get('marks_setting_accepted', 0)}", styles["Normal"]))
            story.append(Paragraph(f"<b>Points for Rejected:</b> {self._safe_get('marks_setting_rejected', 0)}", styles["Normal"]))
        
        story.append(Spacer(1, 0.3 * inch))

        # =====================================================================
        # EXECUTIVE SUMMARY
        # =====================================================================
        story.append(Paragraph("Executive Summary", heading_style))
        
        summary_data = [
            ["Metric", "Value", "Percentage"],
            ["Total Submissions", str(stats["total_submissions"]), "100%"],
            ["Accepted", str(stats["accepted"]), f"{round((stats['accepted'] / stats['total_submissions'] * 100) if stats['total_submissions'] > 0 else 0, 1)}%"],
            ["Rejected", str(stats["rejected"]), f"{round((stats['rejected'] / stats['total_submissions'] * 100) if stats['total_submissions'] > 0 else 0, 1)}%"],
            ["Pending", str(stats["pending"]), f"{round((stats['pending'] / stats['total_submissions'] * 100) if stats['total_submissions'] > 0 else 0, 1)}%"],
            ["Total Points", str(stats["total_points"]), "-"],
            ["Participants", str(stats["unique_participants"]), "-"],
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#006699")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3 * inch))

        # Timeline Chart
        if timeline and len(timeline) > 1:
            chart_path = self._create_timeline_chart(timeline)
            if chart_path:
                story.append(Paragraph("Submission Timeline", heading_style))
                try:
                    story.append(Image(chart_path, width=6 * inch, height=3.5 * inch))
                    story.append(Spacer(1, 0.3 * inch))
                except:
                    pass

        # =====================================================================
        # JUDGE PERFORMANCE
        # =====================================================================
        if judges:
            story.append(PageBreak())
            story.append(Paragraph("Judge Performance Analysis", heading_style))
            
            judge_data = [["Judge", "Reviewed", "Accepted", "Rejected", "Accept %"]]
            for judge in judges:
                judge_data.append([
                    judge["judge_username"],
                    str(judge["total_reviewed"]),
                    str(judge["accepted"]),
                    str(judge["rejected"]),
                    f"{judge['acceptance_rate']}%",
                ])
            
            judge_table = Table(judge_data, colWidths=[2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1 * inch])
            judge_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#006699")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            story.append(judge_table)
            story.append(Spacer(1, 0.3 * inch))

        # =====================================================================
        # TOP CONTRIBUTORS
        # =====================================================================
        story.append(PageBreak())
        story.append(Paragraph(f"Top {len(top_contributors)} Contributors", heading_style))
        
        contrib_data = [["Rank", "Username", "Submissions", "Accepted", "Points"]]
        for c in top_contributors[:20]:  # Limit to 20 for PDF
            contrib_data.append([
                str(c["rank"]),
                c["username"][:25],
                str(c["total_submissions"]),
                str(c["accepted"]),
                str(c["total_points"]),
            ])

        contrib_table = Table(contrib_data, colWidths=[0.6 * inch, 2.5 * inch, 1.3 * inch, 1.3 * inch, 1 * inch])
        contrib_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#006699")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        story.append(contrib_table)
        
        # =====================================================================
        # INSIGHTS
        # =====================================================================
        from app.models.submission import Submission
        submissions = Submission.query.filter_by(contest_id=self.contest.id).all()
        
        if submissions:
            story.append(PageBreak())
            story.append(Paragraph("Article Insights", heading_style))
            
            total_bytes = sum((s.article_word_count or 0) + (s.article_expansion_bytes or 0) for s in submissions)
            total_refs = sum(s.article_reference_count or 0 for s in submissions)
            
            insights_data = [
                ["Metric", "Value"],
                ["Total Bytes Contributed", f"{total_bytes:,}"],
                ["Total References", f"{total_refs:,}"],
                ["Avg Bytes per Article", f"{round(total_bytes / len(submissions), 1):,}"],
                ["Avg References per Article", f"{round(total_refs / len(submissions), 1)}"],
            ]
            
            insights_table = Table(insights_data, colWidths=[3 * inch, 3.5 * inch])
            insights_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#006699")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            story.append(insights_table)

        # Footer
        story.append(PageBreak())
        story.append(Spacer(1, 2 * inch))
        story.append(Paragraph(
            f"<para align=center><b>End of Report</b><br/>"
            f"Generated by WikiContest Platform v2.0<br/>"
            f"{datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}</para>",
            styles["Normal"]
        ))

        doc.build(story)
        return file_path

    def _create_timeline_chart(self, timeline_data):
        """Create timeline chart"""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from datetime import datetime as dt

            dates = [dt.fromisoformat(d["date"]) for d in timeline_data]
            totals = [d["total"] for d in timeline_data]
            accepted = [d["accepted"] for d in timeline_data]
            rejected = [d["rejected"] for d in timeline_data]

            plt.figure(figsize=(10, 6))
            plt.plot(dates, totals, marker="o", linestyle="-", color="#006699", label="Total", linewidth=2)
            plt.plot(dates, accepted, marker="s", linestyle="--", color="#339966", label="Accepted")
            plt.plot(dates, rejected, marker="^", linestyle="--", color="#990000", label="Rejected")

            plt.xlabel("Date", fontsize=12)
            plt.ylabel("Submissions", fontsize=12)
            plt.title("Submission Timeline", fontsize=14, fontweight="bold")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()

            chart_path = f"/tmp/chart_{self.contest.id}_{int(datetime.now().timestamp())}.png"
            plt.savefig(chart_path, dpi=150, bbox_inches="tight")
            plt.close()

            return chart_path
        except Exception as e:
            print(f"Chart error: {e}")
            return None

    def _get_file_path(self, extension):
        """Get file path"""
        if os.path.exists("/data/project"):
            reports_dir = "/data/project/wikicontest/reports"
        else:
            reports_dir = os.path.join(os.path.dirname(__file__), "../../reports")

        os.makedirs(reports_dir, exist_ok=True)
        filename = f"contest_{self.contest.id}_report_{int(datetime.now().timestamp())}.{extension}"
        return os.path.join(reports_dir, filename)