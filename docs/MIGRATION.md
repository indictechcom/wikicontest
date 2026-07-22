# WikiEval Database Migration Guide

Production migration from the legacy schema (comma-separated text columns, username-based foreign keys, flat user fields) to the normalized schema (junction tables, ID-based foreign keys, dedicated request audit table).

---

## Table of Contents

- [1. What Changes](#1-what-changes)
- [2. Prerequisites](#2-prerequisites)
- [3. Migration Steps](#3-migration-steps)
- [4. Verification Queries](#4-verification-queries)
- [5. Rollback Plan](#5-rollback-plan)
- [6. Known Risks and Mitigations](#6-known-risks-and-mitigations)
- [7. Architecture Notes](#7-architecture-notes)

---

## 1. What Changes

### New Tables

| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `contest_jury` | Contest-to-jury-member many-to-many junction | `(contest_id, user_id)` composite |
| `contest_organizers` | Contest-to-organizer many-to-many junction | `(contest_id, user_id)` composite |
| `trusted_member_requests` | Audit trail for trusted-member (creator) requests | `id` autoincrement |

### New Columns

| Table | Column | Type | Notes |
|-------|--------|------|-------|
| `users` | `updated_at` | `DATETIME NOT NULL` | Managed by application |
| `contests` | `slug` | `VARCHAR(250) NOT NULL UNIQUE` | URL-safe slug, auto-generated |
| `contests` | `updated_at` | `DATETIME NOT NULL` | Managed by application |
| `contest_requests` | `updated_at` | `DATETIME NOT NULL` | Managed by application |
| `submissions` | `article_byte_count` | `INT NULL` | Replaces `article_word_count` |
| `submissions` | `updated_at` | `DATETIME NOT NULL` | Managed by application |

### Type Changes

| Table | Column | Old Type | New Type |
|-------|--------|----------|----------|
| `users` | `role` | `VARCHAR(20)` | `ENUM('user','admin','superadmin')` |
| `contests` | `created_by` | `VARCHAR(50)` FK to `users.username` | `INT` FK to `users.id` |
| `submissions` | `article_page_id` | `VARCHAR(50)` | `INT` |
| `submissions` | `status` | `VARCHAR(20)` | `ENUM('pending','accepted','rejected','auto_rejected')` |
| `contest_requests` | `status` | `VARCHAR(20)` | `ENUM('pending','approved','rejected')` |

### Dropped Columns (Data Migrated First)

| Table | Column | Migrated To |
|-------|--------|-------------|
| `contests` | `jury_members` (TEXT, comma-separated usernames) | `contest_jury` junction table |
| `contests` | `organizers` (TEXT, comma-separated usernames) | `contest_organizers` junction table |
| `submissions` | `article_word_count` | `article_byte_count` |
| `users` | `trusted_member_request` (BOOLEAN) | `trusted_member_requests` table |
| `users` | `trusted_member_request_reason` (TEXT) | `trusted_member_requests.reason` |
| `users` | `trusted_member_request_status` (ENUM) | `trusted_member_requests.status` |

### New Indexes

| Table | Index | Columns | Unique |
|-------|-------|---------|--------|
| `contests` | `ix_contests_slug` | `slug` | Yes |
| `contests` | `ix_contests_created_by` | `created_by` | No |
| `submissions` | `ix_submissions_contest_id` | `contest_id` | No |
| `submissions` | `ix_submissions_user_id` | `user_id` | No |
| `submissions` | `ix_submissions_status` | `status` | No |
| `submissions` | `ix_submissions_user_contest` | `(user_id, contest_id)` | No |
| `submissions` | `unique_user_contest_article_submission` | `(user_id, contest_id, article_link(255))` | Yes |
| `contest_requests` | `ix_contest_requests_user_id` | `user_id` | No |
| `contest_requests` | `ix_contest_requests_status` | `status` | No |
| `trusted_member_requests` | `ix_trusted_member_requests_user_id` | `user_id` | No |

---

## 2. Prerequisites

- MySQL 5.7+ or 8.0+ with `REGEXP_REPLACE` support
- Alembic installed in the backend Python environment
- Database user with `ALTER`, `CREATE TABLE`, `DROP COLUMN`, `CREATE INDEX` privileges
- Maintenance window: plan for **1-5 minutes** depending on row counts (backfill loops over contests and submissions)
- **Full database backup** before starting

---

## 3. Migration Steps

### Step 1: Enable Maintenance Mode

Take the application offline to prevent writes during migration.

```bash
# Example: set Flask to return 503
export APP_MAINTENANCE_MODE=1
# or configure your reverse proxy (nginx/caddy) to serve a maintenance page
```

### Step 2: Backup the Database

```bash
mysqldump -u <user> -p --single-transaction --routines --triggers <db_name> \
  > backup_pre_schema_optimization_$(date +%Y%m%d_%H%M%S).sql
```

### Step 3: Record Pre-Migration Row Counts

```sql
SELECT 'users' AS tbl, COUNT(*) AS cnt FROM users
UNION ALL SELECT 'contests', COUNT(*) FROM contests
UNION ALL SELECT 'submissions', COUNT(*) FROM submissions
UNION ALL SELECT 'contest_requests', COUNT(*) FROM contest_requests;
```

Save these numbers for post-migration comparison.

### Step 4: Run Alembic Migration

```bash
cd backend
alembic upgrade head
```

This runs two pending migrations in order:

1. **`c12dc96ccd30`** (schema optimization) — the main migration that:
   - Creates 3 new tables (Phase 1)
   - Runs all data backfills (Phase 2)
   - Alters column types and creates indexes (Phase 3)
   - Drops old columns (Phase 4)

2. **`efdfacdfcbd0`** (unique submissions index) — adds the `unique_user_contest_article_submission` index with a 255-character prefix on `article_link` to avoid MySQL key-length errors.

All operations are idempotent (guarded by `_column_exists` / `_table_exists` checks), so re-running is safe.

### Step 5: Verify the Migration

Run the verification queries from [Section 4](#4-verification-queries) below.

### Step 6: Deploy New Application Code

Deploy the updated backend and frontend together. The new code expects the migrated schema:

- Backend models use junction tables, ID-based FKs, and enum columns
- Backend routes use `JOIN` queries instead of `LIKE` on comma-separated strings
- Frontend auth state persistence fixes prevent stale login state after dev-server restarts

### Step 7: Disable Maintenance Mode

```bash
unset APP_MAINTENANCE_MODE
# or remove the maintenance page from the reverse proxy
```

---

## 4. Verification Queries

Run these after `alembic upgrade head` completes.

### Check Migration State

```sql
-- Should show efdfacdfcbd0
SELECT * FROM alembic_version;
```

### Check New Tables Exist and Have Data

```sql
SELECT 'contest_jury' AS tbl, COUNT(*) AS cnt FROM contest_jury
UNION ALL SELECT 'contest_organizers', COUNT(*) FROM contest_organizers
UNION ALL SELECT 'trusted_member_requests', COUNT(*) FROM trusted_member_requests;
```

### Verify Slug Backfill (No NULL Slugs)

```sql
SELECT COUNT(*) AS null_slugs FROM contests WHERE slug IS NULL;
-- Expected: 0
```

### Verify created_by Is Numeric (No Usernames Left)

```sql
SELECT COUNT(*) AS username_fks
FROM contests
WHERE created_by REGEXP '[^0-9]';
-- Expected: 0
```

### Verify All Creators Are in Organizers

```sql
SELECT c.id, c.name
FROM contests c
LEFT JOIN contest_organizers o
  ON c.id = o.contest_id AND c.created_by = o.user_id
WHERE o.user_id IS NULL AND c.created_by IS NOT NULL;
-- Expected: 0 rows
```

### Verify article_byte_count Backfill

```sql
SELECT COUNT(*) AS missing_byte_count
FROM submissions
WHERE article_byte_count IS NULL;
-- Expected: 0 (if all rows had article_word_count)
```

### Verify Enum Normalization (No Invalid Values)

```sql
SELECT DISTINCT status FROM submissions;
-- Expected: only 'pending', 'accepted', 'rejected', 'auto_rejected'

SELECT DISTINCT role FROM users;
-- Expected: only 'user', 'admin', 'superadmin'

SELECT DISTINCT status FROM contest_requests;
-- Expected: only 'pending', 'approved', 'rejected'
```

### Verify Dropped Columns Are Gone

```sql
SELECT COLUMN_NAME
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'contests'
  AND COLUMN_NAME IN ('jury_members', 'organizers');
-- Expected: 0 rows

SELECT COLUMN_NAME
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'users'
  AND COLUMN_NAME IN ('trusted_member_request', 'trusted_member_request_reason', 'trusted_member_request_status');
-- Expected: 0 rows
```

### Verify Indexes

```sql
SHOW INDEX FROM contests WHERE Key_name LIKE 'ix_%' OR Key_name LIKE 'unique_%';
SHOW INDEX FROM submissions WHERE Key_name LIKE 'ix_%' OR Key_name LIKE 'unique_%';
SHOW INDEX FROM trusted_member_requests WHERE Key_name LIKE 'ix_%';
```

---

## 5. Rollback Plan

### Before Destructive Phase (Phases 1-3 of the migration)

If the migration fails before reaching Phase 4 (column drops), you can safely re-run:

```bash
cd backend
alembic upgrade head
```

All operations are idempotent. If a partial failure occurs, the `_column_exists` guards ensure already-completed steps are skipped on re-run.

### After Full Migration

Once Phase 4 drops the old columns (`jury_members`, `organizers`, `article_word_count`, trusted member fields), rollback requires a database restore:

```bash
# 1. Put the app back in maintenance mode
# 2. Restore from backup
mysql -u <user> -p <db_name> < backup_pre_schema_optimization_*.sql
# 3. Deploy the old application code
# 4. Disable maintenance mode
```

The migration file does include a `downgrade()` function that re-adds dropped columns and reverses type changes, but it does **not** restore the data that was in the dropped columns. Use the backup for a full rollback.

### Alembic Downgrade (Partial, Schema-Only)

```bash
cd backend
alembic downgrade 1a2b3c4d5e6f   # Reverts to pre-migration revision
```

> **Warning**: This re-creates the old columns with empty data. The junction table data and trusted_member_requests data will remain in the database. Use the backup for a clean rollback.

---

## 6. Known Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Comma-separated jury/organizers has >10 members** | The backfill `CROSS JOIN` uses a numbers table (1-10), so contests with >10 jury members or organizers will only migrate the first 10 | Audit `jury_members` and `organizers` columns before migration. If any have >10 entries, update the numbers table in the migration script. |
| **Duplicate slugs** | The slug backfill uses MySQL `REGEXP_REPLACE` which may produce identical slugs for similar contest names | The application-level `generate_slug()` utility appends `-2`, `-3` etc. on collision. Post-migration, check for duplicates: `SELECT slug, COUNT(*) FROM contests GROUP BY slug HAVING COUNT(*) > 1;` |
| **Non-numeric `created_by` values** | The `UPDATE contests SET created_by = u.id` JOIN assumes every `created_by` username exists in `users` | Pre-check: `SELECT created_by FROM contests WHERE created_by NOT IN (SELECT username FROM users);` |
| **Non-numeric `article_page_id` values** | The `CAST(article_page_id AS UNSIGNED)` will set non-numeric values to 0 | The migration sets empty strings to NULL first, then casts. Non-numeric non-empty values become 0. |
| **Cascade delete on submissions** | Deleting a contest now cascades to delete all its submissions | Verify no business logic depends on orphaned submissions surviving contest deletion. |
| **Application code mismatch** | If old app code runs against new schema (or vice versa), queries will fail | Deploy backend and frontend together in Step 6. |

---

## 7. Architecture Notes

### Why Junction Tables

The old `contests.jury_members` and `contests.organizers` columns stored comma-separated usernames as plain text. This made it impossible to:
- Efficiently query "all contests where user X is a jury member"
- Enforce referential integrity (deleted users left dangling names)
- Add/remove a single member without rewriting the entire string

The new `contest_jury` and `contest_organizers` tables use composite primary keys with foreign keys to `users.id`, enabling proper `JOIN` queries and automatic cleanup.

### Why ID-Based Foreign Keys

`contests.created_by` previously stored `users.username` (a string). This is fragile because usernames can change. The migration converts it to `users.id` (an integer), which is immutable and faster to join on.

### Why TrustedMemberRequest Table

The old schema stored trusted-member request state as three columns on the `users` table (`trusted_member_request`, `trusted_member_request_reason`, `trusted_member_request_status`). This meant:
- Only the latest request was tracked (previous requests were overwritten)
- No audit trail of who approved/rejected or when

The new `trusted_member_requests` table stores every request as a separate row with `reviewed_by` and `reviewed_at` fields, providing a complete audit trail.

### Why article_byte_count

The `article_word_count` column was always populated with MediaWiki's `size` value, which is byte count, not word count. The rename corrects the semantic meaning without losing data.

### Migration Phases

The migration `c12dc96ccd30` is organized into 4 phases within a single revision to ensure atomicity:

1. **Additive** — New columns and tables (safe, no data loss)
2. **Backfills** — Copy data from old columns to new structures (safe, reads old data)
3. **Alterations** — Type changes, enum conversions, index creation (requires locks)
4. **Destructive** — Drop old columns (irreversible without backup)

This ordering ensures data is migrated before the source columns are removed.
