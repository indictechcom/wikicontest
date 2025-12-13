# Alembic Model Compatibility Guide

This guide explains how to ensure your SQLAlchemy models are compatible with Alembic's autogenerate feature.

## Requirements for Autogenerate

For Alembic to automatically detect model changes, your models must meet these requirements:

### 1. Models Must Be Imported in `alembic/env.py`

All models must be imported in `alembic/env.py` so Alembic can access their metadata:

```python
# alembic/env.py
from app.models.user import User
from app.models.contest import Contest
from app.models.submission import Submission
```

**Current Status:** ✅ All models are imported

### 2. Models Must Inherit from `db.Model`

All models should inherit from SQLAlchemy's `db.Model` or your base model:

```python
from app.database import db
from app.models.base_model import BaseModel

class User(BaseModel):  # BaseModel inherits from db.Model
    __tablename__ = 'users'
    # ...
```

**Current Status:** ✅ All models inherit from `BaseModel` which inherits from `db.Model`

### 3. Models Must Have `__tablename__` Defined

Each model must explicitly define its table name:

```python
class User(BaseModel):
    __tablename__ = 'users'  # Required
```

**Current Status:** ✅ All models have `__tablename__` defined

### 4. Use Proper SQLAlchemy Column Types

Use standard SQLAlchemy types that Alembic can detect:

✅ **Good (Detectable):**
```python
db.Column(db.String(50), nullable=False)
db.Column(db.Integer, default=0)
db.Column(db.DateTime, default=datetime.utcnow)
db.Column(db.Text, nullable=True)
db.Column(db.Boolean, default=False)
```

❌ **Avoid (May Not Be Detected):**
```python
# Custom types without proper registration
db.Column(MyCustomType())
# Python types instead of SQLAlchemy types
db.Column(str)  # Should be db.String()
```

**Current Status:** ✅ All models use standard SQLAlchemy types

### 5. Foreign Keys Must Use String References

Foreign keys should reference table names as strings:

```python
# ✅ Good
user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

# ❌ Avoid (may cause issues)
user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
```

**Current Status:** ✅ All foreign keys use string references

### 6. Default Values

For callable defaults (like `datetime.utcnow`), pass the function without calling it:

```python
# ✅ Good - function reference
created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# ❌ Bad - calling the function
created_at = db.Column(db.DateTime, default=datetime.utcnow(), nullable=False)
```

**Current Status:** ✅ All datetime defaults are correct

### 7. Constraints and Indexes

Constraints and indexes should be properly defined:

```python
# ✅ Good - Unique constraint
__table_args__ = (
    db.UniqueConstraint('user_id', 'contest_id', name='unique_user_contest_submission'),
)

# ✅ Good - Index on column
username = db.Column(db.String(50), unique=True, nullable=False, index=True)
```

**Current Status:** ✅ Constraints are properly defined

## Current Model Status

### ✅ User Model (`app/models/user.py`)
- Inherits from `BaseModel` ✓
- Has `__tablename__ = 'users'` ✓
- Uses standard SQLAlchemy types ✓
- Foreign keys use string references ✓
- Properly imported in `alembic/env.py` ✓

### ✅ Contest Model (`app/models/contest.py`)
- Inherits from `BaseModel` ✓
- Has `__tablename__ = 'contests'` ✓
- Uses standard SQLAlchemy types ✓
- Foreign keys use string references ✓
- Properly imported in `alembic/env.py` ✓
- **Fixed:** Import statements in `get_leaderboard()` method now use `app.models.*`

### ✅ Submission Model (`app/models/submission.py`)
- Inherits from `BaseModel` ✓
- Has `__tablename__ = 'submissions'` ✓
- Uses standard SQLAlchemy types ✓
- Foreign keys use string references ✓
- Has `__table_args__` for unique constraint ✓
- Properly imported in `alembic/env.py` ✓

## Alembic Configuration Enhancements

The `alembic/env.py` file has been configured with enhanced autogenerate detection:

```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    compare_type=True,              # Detect type changes (e.g., String(50) -> String(100))
    compare_server_default=True,    # Detect default value changes
    include_object=include_object   # Optional filter function
)
```

### What These Options Do

- **`compare_type=True`**: Detects when column types change (e.g., `String(50)` to `String(100)`)
- **`compare_server_default=True`**: Detects when default values change
- **`include_object`**: Allows filtering which objects to include/exclude from migrations

## Testing Autogenerate

To test if autogenerate is working:

1. **Make a small change to a model:**
   ```python
   # app/models/user.py
   class User(BaseModel):
       # ... existing fields ...
       phone = db.Column(db.String(20), nullable=True)  # NEW FIELD
   ```

2. **Generate migration:**
   ```bash
   alembic revision --autogenerate -m "Add phone to users"
   ```

3. **Check the generated file:**
   ```python
   # Should contain:
   def upgrade():
       op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))
   ```

4. **If nothing is generated**, check:
   - Are models imported in `alembic/env.py`?
   - Is the database connection working?
   - Are you using standard SQLAlchemy types?

## Common Issues and Solutions

### Issue: Autogenerate Not Detecting New Columns

**Solution:**
- Ensure the model is imported in `alembic/env.py`
- Check that you're using `db.Column()` with proper types
- Verify the model has `__tablename__` defined

### Issue: Autogenerate Not Detecting Type Changes

**Solution:**
- Ensure `compare_type=True` is set in `alembic/env.py`
- Some type changes may require manual migration (e.g., changing String to Integer)

### Issue: Autogenerate Detecting Too Many Changes

**Solution:**
- Review the generated migration carefully
- Some changes may be false positives
- You can edit the migration file before applying

### Issue: Circular Import Errors

**Solution:**
- Use absolute imports: `from app.models.user import User`
- Avoid importing models in model methods (use lazy imports if needed)
- Ensure `BaseModel` is properly set up

## Best Practices

1. **Always Review Generated Migrations**
   - Alembic may miss some changes or generate incorrect code
   - Review before applying, especially for complex changes

2. **Use Standard SQLAlchemy Types**
   - Stick to `db.String()`, `db.Integer()`, `db.DateTime()`, etc.
   - Avoid custom types unless necessary

3. **Keep Models Simple**
   - Complex logic in models is fine, but keep column definitions straightforward
   - Use properties for computed values instead of database columns

4. **Test Migrations**
   - Always test migrations on a development database first
   - Test both upgrade and downgrade paths

5. **Document Complex Changes**
   - Add comments in migration files for non-obvious changes
   - Explain why manual SQL was needed if autogenerate wasn't sufficient

## Verification Checklist

Before using autogenerate, verify:

- [ ] All models inherit from `BaseModel` (which inherits from `db.Model`)
- [ ] All models have `__tablename__` defined
- [ ] All models are imported in `alembic/env.py`
- [ ] All columns use standard SQLAlchemy types
- [ ] Foreign keys use string references (`'users.id'` not `User.id`)
- [ ] Default values are callable functions (not called functions)
- [ ] `compare_type=True` is set in `alembic/env.py`
- [ ] Database connection is working

## Current Configuration Status

✅ **All requirements met!** Your models are fully compatible with Alembic autogenerate.

The project is configured with:
- Proper model inheritance structure
- All models imported in `alembic/env.py`
- Enhanced autogenerate detection (`compare_type`, `compare_server_default`)
- Proper use of SQLAlchemy types and constraints
- Correct foreign key references

You can now use `alembic revision --autogenerate` to automatically generate migrations from model changes.

