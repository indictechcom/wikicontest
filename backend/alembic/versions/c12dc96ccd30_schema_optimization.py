"""schema optimization

Revision ID: c12dc96ccd30
Revises: 1a2b3c4d5e6f
Create Date: 2026-07-22 17:18:09.536264

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'c12dc96ccd30'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    """Check if a column exists in the given table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.scalar() > 0


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # PHASE 1: Additive column additions (idempotent — skip if exists)
    # -----------------------------------------------------------------------

    if not _column_exists('users', 'updated_at'):
        op.add_column('users', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

    if not _column_exists('contests', 'slug'):
        op.add_column('contests', sa.Column('slug', sa.String(length=250), nullable=True))
    if not _column_exists('contests', 'updated_at'):
        op.add_column('contests', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

    if not _column_exists('contest_requests', 'updated_at'):
        op.add_column('contest_requests', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

    if not _column_exists('submissions', 'article_byte_count'):
        op.add_column('submissions', sa.Column('article_byte_count', sa.Integer(), nullable=True))
    if not _column_exists('submissions', 'updated_at'):
        op.add_column('submissions', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

    # These tables may have been created by db.create_all(); skip creation if they exist
    if not _column_exists('contest_jury', 'contest_id'):
        op.create_table(
            'contest_jury',
            sa.Column('contest_id', sa.Integer(), sa.ForeignKey('contests.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    if not _column_exists('contest_organizers', 'contest_id'):
        op.create_table(
            'contest_organizers',
            sa.Column('contest_id', sa.Integer(), sa.ForeignKey('contests.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    if not _column_exists('trusted_member_requests', 'id'):
        op.create_table(
            'trusted_member_requests',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='trusted_member_request_status_enum'), nullable=False, server_default='pending'),
            sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
        )

    # -----------------------------------------------------------------------
    # PHASE 2: Data backfills (safe even if no data)
    # -----------------------------------------------------------------------

    # Copy article_word_count data to article_byte_count (only where article_byte_count is NULL)
    op.execute("UPDATE submissions SET article_byte_count = article_word_count WHERE article_word_count IS NOT NULL AND article_byte_count IS NULL")

    # Backfill created_by: convert username strings to user IDs
    op.execute("""
        UPDATE contests c
        INNER JOIN users u ON c.created_by = u.username
        SET c.created_by = u.id
    """)

    # Backfill contest_jury from comma-separated jury_members
    op.execute("""
        INSERT IGNORE INTO contest_jury (contest_id, user_id, created_at)
        SELECT c.id, u.id, CURRENT_TIMESTAMP
        FROM contests c
        CROSS JOIN (
            SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
            UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10
        ) numbers
        INNER JOIN users u ON LOWER(TRIM(u.username)) = LOWER(TRIM(
            SUBSTRING_INDEX(SUBSTRING_INDEX(c.jury_members, ',', numbers.n), ',', -1)
        ))
        WHERE c.jury_members IS NOT NULL
          AND c.jury_members != ''
          AND numbers.n <= 1 + LENGTH(c.jury_members) - LENGTH(REPLACE(c.jury_members, ',', ''))
    """)

    # Backfill contest_organizers from comma-separated organizers
    op.execute("""
        INSERT IGNORE INTO contest_organizers (contest_id, user_id, created_at)
        SELECT c.id, u.id, CURRENT_TIMESTAMP
        FROM contests c
        CROSS JOIN (
            SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
            UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10
        ) numbers
        INNER JOIN users u ON LOWER(TRIM(u.username)) = LOWER(TRIM(
            SUBSTRING_INDEX(SUBSTRING_INDEX(c.organizers, ',', numbers.n), ',', -1)
        ))
        WHERE c.organizers IS NOT NULL
          AND c.organizers != ''
          AND numbers.n <= 1 + LENGTH(c.organizers) - LENGTH(REPLACE(c.organizers, ',', ''))
    """)
    # Ensure all creators are also in contest_organizers
    op.execute("""
        INSERT IGNORE INTO contest_organizers (contest_id, user_id, created_at)
        SELECT c.id, c.created_by, CURRENT_TIMESTAMP
        FROM contests c
        WHERE c.created_by IS NOT NULL
    """)

    # Backfill slugs from names
    op.execute("""
        UPDATE contests
        SET slug = LOWER(REGEXP_REPLACE(REGEXP_REPLACE(name, '\\\\s+', '-'), '[^\\\\w\\\\-]+', ''))
        WHERE slug IS NULL
    """)
    op.execute("UPDATE contests SET slug = TRIM(BOTH '-' FROM slug)")
    op.execute("UPDATE contests SET slug = REGEXP_REPLACE(slug, '-{2,}', '-')")

    # Backfill TrustedMemberRequest from existing user columns
    op.execute("""
        INSERT INTO trusted_member_requests (user_id, reason, status, reviewed_by, reviewed_at, created_at, updated_at)
        SELECT id,
               trusted_member_request_reason,
               trusted_member_request_status,
               CASE WHEN trusted_member_request_status IN ('approved', 'rejected') THEN id ELSE NULL END,
               CASE WHEN trusted_member_request_status IN ('approved', 'rejected') THEN created_at ELSE NULL END,
               created_at, created_at
        FROM users
        WHERE trusted_member_request_status IS NOT NULL
    """)

    # -----------------------------------------------------------------------
    # PHASE 3: Column alterations (type changes, constraints)
    # -----------------------------------------------------------------------

    # Remove server_default from updated_at (application manages it now)
    op.alter_column('users', 'updated_at', server_default=None, existing_type=sa.DateTime(), existing_nullable=False)
    op.alter_column('contests', 'updated_at', server_default=None, existing_type=sa.DateTime(), existing_nullable=False)
    op.alter_column('submissions', 'updated_at', server_default=None, existing_type=sa.DateTime(), existing_nullable=False)
    op.alter_column('contest_requests', 'updated_at', server_default=None, existing_type=sa.DateTime(), existing_nullable=False)

    # Set slug NOT NULL + add unique index (column already exists, just modify)
    op.alter_column('contests', 'slug', nullable=False, existing_type=sa.String(length=250))
    try:
        op.create_index('ix_contests_slug', 'contests', ['slug'], unique=True)
    except Exception:
        pass
    try:
        op.create_index('ix_contests_created_by', 'contests', ['created_by'], unique=False)
    except Exception:
        pass

    # Drop old FK on contests.created_by -> users.username, then change column type, then add new FK
    try:
        op.drop_constraint(op.f('contests_ibfk_1'), 'contests', type_='foreignkey')
    except Exception:
        pass
    op.alter_column('contests', 'created_by',
               existing_type=mysql.VARCHAR(length=50),
               type_=sa.Integer(),
               existing_nullable=False)
    op.create_foreign_key(None, 'contests', 'users', ['created_by'], ['id'])

    # users.role enum
    op.execute("UPDATE users SET role = 'user' WHERE role NOT IN ('user', 'admin', 'superadmin')")
    op.alter_column('users', 'role',
               existing_type=mysql.VARCHAR(length=20),
               type_=sa.Enum('user', 'admin', 'superadmin', name='user_role_enum'),
               existing_nullable=False)

    # submissions.article_page_id type change
    op.execute("UPDATE submissions SET article_page_id = NULL WHERE TRIM(article_page_id) = '' OR article_page_id IS NULL")
    op.execute("UPDATE submissions SET article_page_id = CAST(article_page_id AS UNSIGNED) WHERE article_page_id REGEXP '^[0-9]+$'")
    op.alter_column('submissions', 'article_page_id',
               existing_type=mysql.VARCHAR(length=50),
               type_=sa.Integer(),
               existing_nullable=True)

    # submissions.status enum
    op.execute("UPDATE submissions SET status = 'pending' WHERE status NOT IN ('pending', 'accepted', 'rejected', 'auto_rejected')")
    op.alter_column('submissions', 'status',
               existing_type=mysql.VARCHAR(length=20),
               type_=sa.Enum('pending', 'accepted', 'rejected', 'auto_rejected', name='submission_status_enum'),
               existing_nullable=False)

    # submissions FK with ondelete CASCADE
    try:
        op.drop_constraint(op.f('submissions_ibfk_1'), 'submissions', type_='foreignkey')
    except Exception:
        pass
    op.create_foreign_key(None, 'submissions', 'contests', ['contest_id'], ['id'], ondelete='CASCADE')

    # submissions indexes + unique constraint
    for idx_name, tbl, cols in [
        ('ix_submissions_contest_id', 'submissions', ['contest_id']),
        ('ix_submissions_user_id', 'submissions', ['user_id']),
        ('ix_submissions_status', 'submissions', ['status']),
        ('ix_submissions_user_contest', 'submissions', ['user_id', 'contest_id']),
    ]:
        try:
            op.create_index(idx_name, tbl, cols, unique=False)
        except Exception:
            pass
    try:
        op.create_index('unique_user_contest_article_submission', 'submissions', ['user_id', 'contest_id', 'article_link'], unique=True, mysql_length={'article_link': 255})
    except Exception:
        pass

    # contest_requests status enum + indexes
    op.execute("UPDATE contest_requests SET status = 'pending' WHERE status NOT IN ('pending', 'approved', 'rejected')")
    op.alter_column('contest_requests', 'status',
               existing_type=mysql.VARCHAR(length=20),
               type_=sa.Enum('pending', 'approved', 'rejected', name='contest_request_status_enum'),
               existing_nullable=False)
    for idx_name, tbl, cols in [
        ('ix_contest_requests_status', 'contest_requests', ['status']),
        ('ix_contest_requests_user_id', 'contest_requests', ['user_id']),
    ]:
        try:
            op.create_index(idx_name, tbl, cols, unique=False)
        except Exception:
            pass

    # trusted_member_requests index
    try:
        op.create_index('ix_trusted_member_requests_user_id', 'trusted_member_requests', ['user_id'], unique=False)
    except Exception:
        pass

    # -----------------------------------------------------------------------
    # PHASE 4: Drop old columns (destructive — only after app code is updated)
    # -----------------------------------------------------------------------
    # These columns still exist in the DB but are no longer in the models.
    # Only drop them here because the model code no longer references them.
    op.drop_column('contests', 'jury_members')
    op.drop_column('contests', 'organizers')
    op.drop_column('submissions', 'article_word_count')
    op.drop_column('users', 'trusted_member_request')
    op.drop_column('users', 'trusted_member_request_reason')
    op.drop_column('users', 'trusted_member_request_status')


def downgrade() -> None:
    # -----------------------------------------------------------------------
    # Re-add dropped columns (without data restore)
    # -----------------------------------------------------------------------
    op.add_column('users', sa.Column('trusted_member_request', mysql.TINYINT(display_width=1), autoincrement=False, nullable=False, server_default=sa.text("'0'")))
    op.add_column('users', sa.Column('trusted_member_request_reason', mysql.TEXT(), nullable=True))
    op.add_column('users', sa.Column('trusted_member_request_status', mysql.ENUM('pending', 'approved', 'rejected'), nullable=True))

    op.add_column('submissions', sa.Column('article_word_count', mysql.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'submissions', type_='foreignkey')
    op.create_foreign_key(op.f('submissions_ibfk_1'), 'submissions', 'contests', ['contest_id'], ['id'])
    op.drop_index('ix_submissions_status', table_name='submissions')
    op.drop_index('ix_submissions_user_id', table_name='submissions')
    op.drop_index('ix_submissions_contest_id', table_name='submissions')
    op.drop_index('ix_submissions_user_contest', table_name='submissions')
    op.drop_index('unique_user_contest_article_submission', table_name='submissions')
    op.alter_column('submissions', 'article_page_id',
               existing_type=sa.Integer(),
               type_=mysql.VARCHAR(length=50),
               existing_nullable=True)
    op.alter_column('submissions', 'status',
               existing_type=sa.Enum('pending', 'accepted', 'rejected', 'auto_rejected', name='submission_status_enum'),
               type_=mysql.VARCHAR(length=20),
               existing_nullable=False)
    op.alter_column('submissions', 'score_breakdown',
               existing_type=mysql.TEXT(),
               comment='JSON breakdown of score calculation for automated scoring',
               existing_nullable=True)
    op.alter_column('submissions', 'evaluation_reason',
               existing_type=mysql.TEXT(),
               comment='Reason for rejection or success message from automated evaluation',
               existing_nullable=True)
    op.alter_column('submissions', 'ref_reused_count',
               existing_type=sa.Integer(),
               server_default=sa.text("'0'"),
               existing_nullable=True)
    op.alter_column('submissions', 'ref_new_count',
               existing_type=sa.Integer(),
               server_default=sa.text("'0'"),
               existing_nullable=True)
    # Copy article_byte_count back to article_word_count so downgrade preserves data
    op.execute("UPDATE submissions SET article_word_count = article_byte_count WHERE article_byte_count IS NOT NULL")
    op.drop_column('submissions', 'updated_at')
    op.drop_column('submissions', 'article_byte_count')

    op.drop_index('ix_contest_requests_user_id', table_name='contest_requests')
    op.drop_index('ix_contest_requests_status', table_name='contest_requests')
    op.alter_column('contest_requests', 'status',
               existing_type=sa.Enum('pending', 'approved', 'rejected', name='contest_request_status_enum'),
               type_=mysql.VARCHAR(length=20),
               existing_nullable=False)
    op.drop_column('contest_requests', 'updated_at')

    op.add_column('contests', sa.Column('organizers', mysql.TEXT(), nullable=True))
    op.add_column('contests', sa.Column('jury_members', mysql.TEXT(), nullable=True))
    op.drop_index('ix_contests_slug', table_name='contests')
    op.drop_index('ix_contests_created_by', table_name='contests')
    op.drop_constraint(None, 'contests', type_='foreignkey')
    op.create_foreign_key(op.f('contests_ibfk_1'), 'contests', 'users', ['created_by'], ['username'])
    op.alter_column('contests', 'created_by',
               existing_type=sa.Integer(),
               type_=mysql.VARCHAR(length=50),
               existing_nullable=False)
    op.alter_column('contests', 'automated_settings',
               existing_type=mysql.TEXT(),
               comment='Automated scoring configuration (eligibility + evaluation criteria)',
               existing_nullable=True)
    op.drop_column('contests', 'updated_at')
    op.drop_column('contests', 'slug')

    op.alter_column('users', 'role',
               existing_type=sa.Enum('user', 'admin', 'superadmin', name='user_role_enum'),
               type_=mysql.VARCHAR(length=20),
               existing_nullable=False)
    op.drop_column('users', 'updated_at')
