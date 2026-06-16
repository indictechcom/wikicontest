"""Add ref_new_count and ref_reused_count columns to submissions table

Revision ID: 2b7c1a9d4c3e
Revises: 195a1fb1d56e

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "2b7c1a9d4c3e"
down_revision = "195a1fb1d56e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("submissions")]

    if "ref_new_count" not in columns:
        op.add_column(
            "submissions",
            sa.Column("ref_new_count", sa.Integer(), nullable=True, server_default="0"),
        )

    if "ref_reused_count" not in columns:
        op.add_column(
            "submissions",
            sa.Column("ref_reused_count", sa.Integer(), nullable=True, server_default="0"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("submissions")]

    if "ref_reused_count" in columns:
        op.drop_column("submissions", "ref_reused_count")

    if "ref_new_count" in columns:
        op.drop_column("submissions", "ref_new_count")
