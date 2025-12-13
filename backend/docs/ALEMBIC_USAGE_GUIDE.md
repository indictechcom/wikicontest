# Alembic Database Migrations Guide

This guide explains how to use Alembic for database migrations in the WikiContest application. Alembic is a database migration tool for SQLAlchemy that provides version control for database schemas, similar to Git for code.

## Overview

Alembic is configured to work with Flask's application factory pattern. The database URL is automatically retrieved from the Flask app configuration, so you don't need to set it manually in `alembic.ini`.

### How Alembic Works

Alembic tracks database schema changes through:

1. **Migration Files**: Python files in `alembic/versions/` that define schema changes
2. **Version Tracking**: An `alembic_version` table in your database stores the current migration version
3. **Migration Chain**: Each migration points to the previous one, forming a linked list
4. **Upgrade/Downgrade**: Each migration has `upgrade()` (apply) and `downgrade()` (rollback) functions

### Key Components

- **`alembic.ini`**: Configuration file pointing to migration directory
- **`alembic/env.py`**: Environment setup that connects to Flask app and loads models
- **`alembic/versions/`**: Directory containing all migration files
- **`alembic_version` table**: Database table tracking current migration version

## Initial Setup

Alembic is already initialized. If you need to reinitialize:

```bash
alembic init alembic
```

## Creating Migrations

### Auto-generate Migration from Models (Recommended)

Alembic can automatically detect changes in your SQLAlchemy models and generate migration code:

```bash
# Using Makefile (recommended)
make migrate-create MSG="Description of changes"

# Direct Alembic command
alembic revision --autogenerate -m "Description of changes"

# Example:
alembic revision --autogenerate -m "Add user profile fields"
```

**How it works:**
1. Alembic scans your models (imported in `alembic/env.py`)
2. Compares them to the current database schema
3. Generates migration code with `upgrade()` and `downgrade()` functions
4. Creates a new file in `alembic/versions/` with a unique revision ID

**Important:** Always review auto-generated migrations before applying them!

### Manual Migration

To create an empty migration file for manual SQL or complex operations:

```bash
alembic revision -m "Description of changes"
```

Then edit the generated file in `alembic/versions/` to add your migration logic:

```python
def upgrade():
    # Your custom SQL here
    op.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(20)")

def downgrade():
    # Reverse operation
    op.execute("ALTER TABLE users DROP COLUMN phone")
```

## Running Migrations

### Apply All Pending Migrations

```bash
# Using Makefile (recommended)
make db-upgrade

# Direct Alembic command - upgrade to latest version
alembic upgrade head

# Upgrade to a specific revision
alembic upgrade <revision_id>

# Upgrade one step forward
alembic upgrade +1
```

**What happens:**
1. Alembic checks the `alembic_version` table for current version
2. Finds all migrations between current and target
3. Executes `upgrade()` functions in order
4. Updates `alembic_version` table with new version

### Rollback Migrations

```bash
# Using Makefile (recommended)
make db-downgrade

# Direct Alembic command - rollback one revision
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision_id>

# Rollback all migrations (back to base)
alembic downgrade base
```

**What happens:**
1. Alembic gets current version from `alembic_version` table
2. Finds the previous migration in the chain
3. Executes current migration's `downgrade()` function
4. Updates `alembic_version` table to previous revision

## Checking Migration Status

```bash
# Using Makefile (recommended)
make db-current    # Show current revision
make db-history    # Show migration history

# Direct Alembic commands
alembic current              # Show current revision
alembic history              # Show migration history
alembic history --verbose    # Detailed history with dates
alembic heads                # Show all head revisions (for branching)
```

**Understanding the output:**

- **`alembic current`**: Shows the revision ID currently applied to your database
  ```
  82d86aae966e (head)
  ```

- **`alembic history`**: Shows the migration chain
  ```
  82d86aae966e -> abc123def456 (head), Add user bio field
  82d86aae966e (initial), Initial migration
  ```

## Migration Workflow

### Complete Example: Adding a New Field

1. **Modify your model** in `app/models/`:
   ```python
   # app/models/user.py
   class User(BaseModel):
       username = db.Column(db.String(50), unique=True, nullable=False)
       email = db.Column(db.String(100), unique=True, nullable=False)
       phone = db.Column(db.String(20), nullable=True)  # NEW FIELD
   ```

2. **Generate migration**:
   ```bash
   make migrate-create MSG="Add phone number to users"
   # or
   alembic revision --autogenerate -m "Add phone number to users"
   ```

3. **Review the generated migration** in `alembic/versions/`:
   ```python
   def upgrade():
       op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))
   
   def downgrade():
       op.drop_column('users', 'phone')
   ```

4. **Test the migration**:
   ```bash
   make db-upgrade
   # or
   alembic upgrade head
   ```

5. **Verify the change**:
   ```bash
   make db-current
   # Check your database to confirm the column was added
   ```

6. **Commit to version control**:
   ```bash
   git add alembic/versions/[revision]_add_phone_number_to_users.py
   git commit -m "Add phone number field to users"
   ```

### Daily Development Workflow

```bash
# 1. Make model changes
# 2. Create migration
make migrate-create MSG="Description"

# 3. Review generated file
# 4. Apply migration
make db-upgrade

# 5. Test your application
# 6. If issues, rollback
make db-downgrade

# 7. Fix and repeat
```

## Important Notes

- **Always review auto-generated migrations** before applying them - Alembic may miss some changes
- **Test migrations on a development database** first - Never apply untested migrations to production
- **Backup your database** before running migrations in production
- **Never edit existing migration files** that have been applied to production - Create new migrations for fixes
- The database URL is read from Flask app configuration (`SQLALCHEMY_DATABASE_URI`) - No need to set in `alembic.ini`
- All models must be imported in `alembic/env.py` for autogenerate to work
- Migrations run in transactions - If a migration fails, it automatically rolls back
- Use descriptive migration messages - They help track changes over time

## Configuration

The Alembic configuration is in:
- `alembic.ini` - Main configuration file
- `alembic/env.py` - Environment setup (connects to Flask app)

## Advanced Commands

### View SQL Without Executing

```bash
# See what SQL would be executed
alembic upgrade head --sql

# See downgrade SQL
alembic downgrade -1 --sql
```

### Stamping (Mark Version Without Running)

```bash
# Mark database as being at a specific version (useful for existing databases)
alembic stamp <revision_id>

# Mark as current head
alembic stamp head
```

### Merging Branches

If you have multiple migration branches (from parallel development):

```bash
# Merge two branches
alembic merge -m "Merge user and contest changes" <revision1> <revision2>
```

## Troubleshooting

### "Target database is not up to date"

Your database is behind. Apply pending migrations:
```bash
make db-upgrade
# or
alembic upgrade head
```

### "Can't locate revision identified by 'xxx'"

The migration file is missing. Options:
1. Restore the missing migration file from version control
2. Or stamp the database to skip it (if safe):
   ```bash
   alembic stamp <revision_id>
   ```

### "Multiple heads detected"

Multiple migration branches exist. Merge them:
```bash
alembic merge -m "Merge branches" <head1> <head2>
```

### Migration Not Detecting Model Changes

Ensure all models are imported in `alembic/env.py`:
```python
from app.models.user import User
from app.models.contest import Contest
from app.models.submission import Submission
```

Also check:
- Models inherit from `db.Model` (or your base model)
- Models are properly defined with columns
- Database connection is working

### Database Connection Errors

- Check that your `.env` file has the correct `DATABASE_URL`
- Verify the database server is running
- Ensure database credentials are correct
- Test connection: `python -c "from app import app; print(app.config['SQLALCHEMY_DATABASE_URI'])"`

### Migration Conflicts

If you have conflicts with existing migrations:
1. Check current revision: `alembic current`
2. Review migration history: `alembic history`
3. Resolve conflicts manually or create a merge migration
4. Consider using `alembic stamp` if you need to align versions

## Best Practices

1. **One logical change per migration** - Keep migrations focused and atomic
2. **Use descriptive names** - Migration names should clearly describe the change
   ```bash
   # Good
   alembic revision --autogenerate -m "Add user phone number field"
   
   # Bad
   alembic revision --autogenerate -m "update"
   ```

3. **Test both upgrade and downgrade** - Ensure migrations are reversible
   ```bash
   alembic upgrade head
   # Test application
   alembic downgrade -1
   # Verify rollback worked
   alembic upgrade head
   ```

4. **Don't modify applied migrations** - If a migration has been applied to production, create a new migration for fixes

5. **Review auto-generated code** - Alembic may miss some changes or generate incorrect code

6. **Document complex migrations** - Add comments for non-obvious changes or data transformations

7. **Commit migration files** - Always commit migration files to version control with your code changes

8. **Backup before production** - Always backup your database before running migrations in production

9. **Test on staging first** - Test migrations on a staging environment that mirrors production

10. **Use transactions** - Alembic wraps migrations in transactions by default, but be aware of database-specific limitations

## Integration with Existing Migrations

The project also has custom migration scripts in the `migrations/` directory. These can coexist with Alembic migrations:

- **Custom migrations** (`migrations/`): For one-time data migrations or complex changes
- **Alembic migrations** (`alembic/versions/`): For schema version control

**Guidelines:**
- **Use Alembic** for all new schema changes (adding columns, tables, indexes, etc.)
- **Use custom scripts** for data migrations (backfilling data, one-time transformations)
- Both can coexist, but prefer Alembic for schema changes

## Quick Reference

### Common Commands

```bash
# Using Makefile (recommended)
make migrate-create MSG="Description"  # Create migration
make db-upgrade                        # Apply migrations
make db-downgrade                      # Rollback one
make db-current                        # Check status
make db-history                        # View history

# Direct Alembic commands
alembic revision --autogenerate -m "Description"
alembic upgrade head
alembic downgrade -1
alembic current
alembic history
```

### Migration File Structure

Each migration file contains:
- `revision`: Unique identifier (hash-based)
- `down_revision`: Points to previous migration (None = first)
- `upgrade()`: Function to apply the migration
- `downgrade()`: Function to reverse the migration

### Understanding the Chain

Migrations form a linked list:
```
base → 82d86aae966e → abc123def456 → xyz789ghi012 → head
```

Each migration's `down_revision` points to the previous one, allowing Alembic to:
- Track the migration chain
- Apply migrations in order
- Rollback migrations in reverse order

