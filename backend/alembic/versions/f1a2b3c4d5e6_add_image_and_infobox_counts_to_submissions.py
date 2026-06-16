"""Add image_count and infobox_count columns to submissions table

Revision ID: f1a2b3c4d5e6
Revises: b3f7a9c2d1e4

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "f1a2b3c4d5e6"
down_revision = "b3f7a9c2d1e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("submissions")]

    if "image_count" not in columns:
        op.add_column(
            "submissions",
            sa.Column("image_count", sa.Integer(), nullable=True),
        )

    if "infobox_count" not in columns:
        op.add_column(
            "submissions",
            sa.Column("infobox_count", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("submissions")]

    if "infobox_count" in columns:
        op.drop_column("submissions", "infobox_count")

    if "image_count" in columns:
        op.drop_column("submissions", "image_count")
