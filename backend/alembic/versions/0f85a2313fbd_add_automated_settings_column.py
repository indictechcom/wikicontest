"""add_automated_settings_column

Revision ID: 0f85a2313fbd
Revises: 2b7c1a9d4c3e
Create Date: 2026-03-17

Adds automated_settings column to contests table for automated scoring mode.
This column stores eligibility criteria and evaluation parameters as JSON.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0f85a2313fbd'
down_revision = '2b7c1a9d4c3e'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add automated_settings column to contests table.
    
    Structure stored as JSON:
    {
        "enabled": true,
        "eligibility": {
            "min_edits": 100,
            "min_outgoing_links": 3
        },
        "evaluation": {
            "points_per_accepted": 10,
            "points_per_byte": 0.001,
            "points_per_incoming_link": 2,
            "points_per_outgoing_link": 1,
            "points_per_category": 1,
            "points_per_new_reference": 3,
            "points_per_reused_reference": 1,
            "points_per_infobox": 5,
            "points_per_image": 2
        }
    }
    """
    op.add_column(
        'contests',
        sa.Column(
            'automated_settings',
            sa.Text(),
            nullable=True,
            comment='Automated scoring configuration (eligibility + evaluation criteria)'
        )
    )


def downgrade():
    """Remove automated_settings column from contests table."""
    op.drop_column('contests', 'automated_settings')
