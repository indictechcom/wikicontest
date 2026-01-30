"""merge report feature and outreach dashboard migrations

Revision ID: e4e56960f418
Revises: cb863878e0d1, d55c876a1323
Create Date: 2026-01-30 20:30:29.797250

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4e56960f418'
down_revision = ('cb863878e0d1', 'd55c876a1323')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

