"""add_evaluation_details_columns

Revision ID: 1a2b3c4d5e6f
Revises: 0f85a2313fbd
Create Date: 2026-03-21

Adds evaluation_reason and score_breakdown columns to submissions table
for displaying automated scoring details.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = '0f85a2313fbd'
branch_labels = None
depends_on = None


def upgrade():
    """Add evaluation_reason and score_breakdown columns to submissions table."""
    op.add_column(
        'submissions',
        sa.Column(
            'evaluation_reason',
            sa.Text(),
            nullable=True,
            comment='Reason for rejection or success message from automated evaluation'
        )
    )
    op.add_column(
        'submissions',
        sa.Column(
            'score_breakdown',
            sa.Text(),
            nullable=True,
            comment='JSON breakdown of score calculation for automated scoring'
        )
    )


def downgrade():
    """Remove evaluation_reason and score_breakdown columns from submissions table."""
    op.drop_column('submissions', 'score_breakdown')
    op.drop_column('submissions', 'evaluation_reason')
