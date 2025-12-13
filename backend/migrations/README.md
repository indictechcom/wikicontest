# Database Migrations

This directory contains database migration scripts for the WikiContest application.

## Migration Scripts

### Add Article Metadata to Submissions

**File**: `add_article_metadata_to_submissions.py`

**Purpose**: Adds new columns to the `submissions` table to store article metadata fetched from MediaWiki API:
- `article_author` - Author/creator of the article
- `article_created_at` - When article was created
- `article_word_count` - Word count/size of article
- `article_page_id` - MediaWiki page ID

### Add Expansion Bytes to Submissions

**File**: `add_expansion_bytes_to_submissions.py`

**Purpose**: Adds the `article_expansion_bytes` column to track bytes added to articles since contest start.

### Add Size at Start to Submissions

**File**: `add_size_at_start_to_submissions.py`

**Purpose**: Adds the `article_size_at_start` column to store the article size at the contest start date.

## Automatic Migration

The application will automatically run migrations on startup if the columns don't exist. You don't need to run them manually unless you prefer to do so.

The migration logic is in `app/__init__.py` in the `migrate_database()` function, which is called during application startup.

## Manual Migration

If you want to run migrations manually, use the Python scripts:

### Option 1: Run Individual Migration

```bash
# From the backend directory
python migrations/add_article_metadata_to_submissions.py
python migrations/add_expansion_bytes_to_submissions.py
python migrations/add_size_at_start_to_submissions.py
```

### Option 2: Run All Migrations

```bash
# The application runs all migrations automatically on startup
python main.py
```

## Migration Safety

- All new columns are **nullable**, so existing submissions will continue to work
- Migrations are **safe to run multiple times** - they check if columns exist before adding them
- If you're starting with a fresh database, `db.create_all()` will create all columns automatically
- Migrations use SQLAlchemy's `text()` function for raw SQL execution

## Migration Script Structure

Each migration script follows this pattern:

1. **Path Setup**: Adds the backend directory to Python path
2. **Import**: Imports the Flask app and database instance
3. **Check**: Verifies if the column already exists
4. **Execute**: Adds the column if it doesn't exist
5. **Commit**: Commits the changes to the database

## Notes

- Migrations are idempotent - running them multiple times is safe
- Migrations use `ALTER TABLE` statements, so they work with existing data
- For production deployments, consider using Flask-Migrate (Alembic) for more robust migration management
- Always backup your database before running migrations in production

## Future Migrations

When adding new migrations:

1. Create a new Python script in this directory
2. Follow the naming convention: `add_<feature>_to_<table>.py`
3. Include proper error handling
4. Add checks to prevent duplicate column creation
5. Update this README with migration details
6. Test the migration on a development database first
