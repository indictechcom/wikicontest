"""add_contest_report_table

Revision ID: xxxxxxxxxxxx  # Alembic automatically generates this
Revises: yyyyyyyyyyyy     # Previous migration ID
Create Date: 2026-01-21 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'cb863878e0d1'
down_revision = 'de4074ff4ff8'
branch_labels = None
depends_on = None


def upgrade():
    """Create contest_reports table"""
    
    # Create contest_reports table
    op.create_table(
        'contest_reports',
        
        # Primary key
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        
        # Foreign keys
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('generated_by', sa.Integer(), nullable=False),
        
        # Report configuration
        sa.Column('report_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        
        # File storage
        sa.Column('file_path', sa.String(length=500), nullable=True),
        
        # Error handling
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Report parameters (JSON)
        sa.Column('report_metadata', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Primary key constraint
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(['contest_id'], ['contests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_contest_reports_contest_id', 'contest_reports', ['contest_id'])
    op.create_index('idx_contest_reports_generated_by', 'contest_reports', ['generated_by'])
    op.create_index('idx_contest_reports_status', 'contest_reports', ['status'])


def downgrade():
    """Drop contest_reports table"""
    
    # Drop indexes first
    op.drop_index('idx_contest_reports_status', table_name='contest_reports')
    op.drop_index('idx_contest_reports_generated_by', table_name='contest_reports')
    op.drop_index('idx_contest_reports_contest_id', table_name='contest_reports')
    
    # Drop table
    op.drop_table('contest_reports')