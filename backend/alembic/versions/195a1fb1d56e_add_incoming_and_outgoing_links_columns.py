"""add incoming and outgoing links columns

Revision ID: 195a1fb1d56e
Revises: f1a2b3c4d5e6
Create Date: 2026-02-06 17:25:37.027375

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '195a1fb1d56e'
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("submissions")]

    if "incoming_links" not in columns:
        op.add_column(
            "submissions",
            sa.Column("incoming_links", sa.Integer(), nullable=True),
        )

    if "outgoing_links" not in columns:
        op.add_column(
            "submissions",
            sa.Column("outgoing_links", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("submissions")]

    if "outgoing_links" in columns:
        op.drop_column("submissions", "outgoing_links")

    if "incoming_links" in columns:
        op.drop_column("submissions", "incoming_links")
