# pylint: disable=broad-exception-caught,broad-exception-raised
"""
Report Routes for WikiContest Application
ENHANCED: Better error handling and detailed logging
"""

from flask import Blueprint, request, send_file, jsonify
from app.middleware.auth import require_auth, handle_errors
from app.models.contest import Contest
from app.models.contest_report import ContestReport
from app.utils.report_builder import CSVReportBuilder, PDFReportBuilder
from app.utils.report_queries import (
    get_submission_statistics,
    get_top_contributors
)
from app.database import db
import os
import traceback

report_bp = Blueprint('report', __name__)


@report_bp.route('/contest/<int:contest_id>/generate', methods=['POST'])
@require_auth
@handle_errors
def generate_report(contest_id):
    """Generate a contest report (CSV or PDF) with comprehensive error handling"""

    report = None

    try:
        # Step 1: Get current user
        current_user = request.current_user

        # Step 2: Fetch contest
        contest = Contest.query.get(contest_id)
        if not contest:
            return jsonify({'error': 'Contest not found'}), 404

        # Step 3: Check permissions
        is_admin = current_user.is_admin()
        is_creator = current_user.is_contest_creator(contest)
        is_organizer = current_user.is_contest_organizer(contest)

        if not (is_admin or is_creator or is_organizer):
            return jsonify({'error': 'Insufficient permissions'}), 403

        # Step 4: Parse request
        data = request.get_json() or {}
        report_type = data.get('report_type', 'csv')
        top_n = data.get('top_n', 100)

        if report_type not in ['csv', 'pdf']:
            return jsonify({
                'error': 'Invalid report type. Must be "csv" or "pdf"'
            }), 400

        # Step 5: Validate contest has submissions
        from app.models.submission import Submission
        submission_count = Submission.query.filter_by(contest_id=contest_id).count()

        if submission_count == 0:
            print(f" Warning: No submissions to report on")
            # Continue anyway - empty report is valid

        # Step 6: Create report record
        metadata = {'top_n': top_n}

        try:
            report = ContestReport(
                contest_id=contest_id,
                report_type=report_type,
                generated_by=current_user.id,
                report_metadata=metadata
            )
            db.session.add(report)
            db.session.commit()
        except Exception as db_error:
            print(f"Database error creating report: {db_error}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to create report record',
                'details': str(db_error)
            }), 500

        # Step 7: Generate report
        report.status = 'processing'
        db.session.commit()

        report_metadata = report.get_metadata() or {}
        file_path = None

        try:
            if report_type == 'csv':
                builder = CSVReportBuilder(contest, report_metadata)
                file_path = builder.generate()
            else:  # pdf
                builder = PDFReportBuilder(contest, report_metadata)
                file_path = builder.generate()

            # Verify file exists
            if not os.path.exists(file_path):
                raise Exception(f"Generated file not found at {file_path}")

            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise Exception("Generated file is empty")

        except Exception as gen_error:
            traceback.print_exc()

            report.status = 'failed'
            report.error_message = str(gen_error)
            db.session.commit()

            return jsonify({
                'error': 'Report generation failed',
                'details': str(gen_error),
                'type': type(gen_error).__name__
            }), 500

        # Update status
        report.status = 'completed'
        report.file_path = file_path
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Report generated successfully',
            'report': report.to_dict()
        }), 200

    except Exception as e:
        traceback.print_exc()

        # Update report status if it was created
        if report:
            try:
                report.status = 'failed'
                report.error_message = str(e)
                db.session.commit()
            except Exception as db_error:
                print(f"Failed to update report status: {db_error}")
                db.session.rollback()

        return jsonify({
            'error': 'Report generation failed',
            'details': str(e),
            'type': type(e).__name__
        }), 500


@report_bp.route('/contest/<int:contest_id>/reports', methods=['GET'])
@require_auth
@handle_errors
def list_reports(contest_id):
    """List all reports for a contest"""
    try:

        current_user = request.current_user
        contest = Contest.query.get_or_404(contest_id)

        # Check permissions
        if not (current_user.is_admin() or
                current_user.is_contest_creator(contest) or
                current_user.is_contest_organizer(contest)):
            return jsonify({'error': 'Insufficient permissions'}), 403

        # Fetch reports
        reports = ContestReport.query.filter_by(
            contest_id=contest_id
        ).order_by(
            ContestReport.id.desc()
        ).all()

        return jsonify({
            'success': True,
            'reports': [r.to_dict() for r in reports]
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@report_bp.route('/report/<int:report_id>/download', methods=['GET'])
@require_auth
@handle_errors
def download_report(report_id):
    """Download a generated report"""
    try:

        current_user = request.current_user
        report = ContestReport.query.get_or_404(report_id)
        contest = report.contest

        # Check permissions
        if not (current_user.is_admin() or
                current_user.is_contest_creator(contest) or
                current_user.is_contest_organizer(contest)):
            return jsonify({'error': 'Insufficient permissions'}), 403

        # Check if report is ready
        if report.status != 'completed':
            return jsonify({
                'error': 'Report not ready',
                'status': report.status,
                'error_message': report.error_message
            }), 400

        # Check if file exists
        if not report.file_path:
            return jsonify({'error': 'Report file path missing'}), 404

        if not os.path.exists(report.file_path):
            return jsonify({'error': 'Report file not found on disk'}), 404

        # Send file
        filename = f"contest_{report.contest_id}_report.{report.report_type}"

        return send_file(
            report.file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv' if report.report_type == 'csv' else 'application/pdf'
        )

    except Exception as e:
        print(f" Download error: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to download report: {str(e)}'}), 500


@report_bp.route('/report/<int:report_id>/status', methods=['GET'])
@require_auth
@handle_errors
def report_status(report_id):
    """Check report generation status"""
    try:
        current_user = request.current_user
        report = ContestReport.query.get_or_404(report_id)
        contest = report.contest

        # Check permissions
        if not (current_user.is_admin() or
                current_user.is_contest_creator(contest) or
                current_user.is_contest_organizer(contest)):
            return jsonify({'error': 'Insufficient permissions'}), 403

        return jsonify({
            'success': True,
            'report': report.to_dict()
        }), 200

    except Exception as e:
        print(f" Status check error: {e}")
        return jsonify({'error': str(e)}), 500


@report_bp.route('/contest/<int:contest_id>/preview', methods=['GET'])
@require_auth
@handle_errors
def preview_report(contest_id):
    """Preview report data without generating full file"""
    try:

        current_user = request.current_user
        contest = Contest.query.get_or_404(contest_id)

        # Check permissions
        if not (current_user.is_admin() or
                current_user.is_contest_creator(contest) or
                current_user.is_contest_organizer(contest)):
            return jsonify({'error': 'Insufficient permissions'}), 403

        # Get preview parameters
        top_n = request.args.get('top_n', 10, type=int)

        # Fetch preview data with error handling
        try:
            stats = get_submission_statistics(contest_id)
        except Exception as e:
            print(f"    Statistics failed: {e}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to fetch statistics',
                'details': str(e)
            }), 500

        try:
            top_contributors = get_top_contributors(contest_id, limit=top_n)
        except Exception as e:
            print(f"    Contributors failed: {e}")
            traceback.print_exc()
            top_contributors = []

        return jsonify({
            'success': True,
            'preview': {
                'summary': stats,
                'top_contributors': top_contributors,
                'contest': {
                    'id': contest.id,
                    'name': contest.name,
                    'start_date': contest.start_date.isoformat() if contest.start_date else None,
                    'end_date': contest.end_date.isoformat() if contest.end_date else None,
                }
            }
        }), 200

    except Exception as e:
        print(f" Preview error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@report_bp.route('/report/<int:report_id>', methods=['DELETE'])
@require_auth
@handle_errors
def delete_report(report_id):
    """Delete a generated report"""
    try:

        current_user = request.current_user
        report = ContestReport.query.get_or_404(report_id)
        contest = report.contest

        # Check permissions (only admin or contest creator)
        if not (current_user.is_admin() or current_user.is_contest_creator(contest)):
            return jsonify({'error': 'Insufficient permissions'}), 403

        # Delete file if it exists
        if report.file_path and os.path.exists(report.file_path):
            try:
                os.remove(report.file_path)
            except Exception as e:
                print(f"  File delete error: {e}")

        # Delete database record
        db.session.delete(report)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Report deleted successfully'
        }), 200

    except Exception as e:
        print(f" Delete error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@report_bp.route('/health', methods=['GET'])
def report_health():
    """Health check endpoint for report system"""
    dependencies = {
        'database': False,
        'reportlab': False,
        'matplotlib': False,
        'reports_directory': False
    }

    # Check database
    try:
        db.session.execute('SELECT 1')
        dependencies['database'] = True
    except Exception as e:
        print(f" Database check failed: {e}")

    # Check reportlab
    try:
        import reportlab
        dependencies['reportlab'] = True
    except ImportError:
        print(" reportlab not installed")

    # Check matplotlib
    try:
        import matplotlib
        dependencies['matplotlib'] = True
    except ImportError:
        print(" matplotlib not installed")

    # Check reports directory
    try:
        if os.path.exists('/data/project'):
            reports_dir = '/data/project/wikicontest/reports'
        else:
            reports_dir = os.path.join(os.path.dirname(__file__), '../../reports')

        os.makedirs(reports_dir, exist_ok=True)
        test_file = os.path.join(reports_dir, '.health_check')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        dependencies['reports_directory'] = True
    except Exception as e:
        print(f" Reports directory check failed: {e}")

    all_ok = all(dependencies.values())

    return jsonify({
        'status': 'healthy' if all_ok else 'degraded',
        'dependencies': dependencies,
        'message': 'All dependencies available' if all_ok else 'Some dependencies missing'
    }), 200 if all_ok else 503