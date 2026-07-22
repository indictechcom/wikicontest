"""add unique submissions index with prefix

Revision ID: efdfacdfcbd0
Revises: c12dc96ccd30
Create Date: 2026-07-22 19:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'efdfacdfcbd0'
down_revision = 'c12dc96ccd30'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        CREATE UNIQUE INDEX unique_user_contest_article_submission
        ON submissions (user_id, contest_id, article_link(255))
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP INDEX unique_user_contest_article_submission ON submissions"))
