"""
Alembic environment configuration for WikiContest Flask Application

This file configures Alembic to work with the Flask application factory pattern.
It automatically detects the database URL from the Flask app configuration.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import the Flask app and database
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import the Flask app factory and database
from app import create_app
from app.database import db

# Import all models to ensure they are registered with SQLAlchemy
# This is required for Alembic to detect model changes
from app.models.user import User  # pylint: disable=unused-import
from app.models.contest import Contest  # pylint: disable=unused-import
from app.models.submission import Submission  # pylint: disable=unused-import

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = db.metadata

# Optional: Filter function to include/exclude objects from autogenerate
def include_object(object, name, type_, reflected, compare_to):
    """
    Optional function to filter which objects Alembic should consider.
    
    This can be used to exclude certain tables or objects from migration generation.
    By default, include all objects.
    
    Args:
        object: The object being considered
        name: Name of the object
        type_: Type of object ('table', 'column', 'index', etc.)
        reflected: Whether the object is from the database
        compare_to: The object from the model metadata
    
    Returns:
        bool: True to include, False to exclude
    """
    # Include all objects by default
    # You can add custom logic here to exclude specific tables/objects
    # For example, to exclude alembic_version table:
    # if name == 'alembic_version':
    #     return False
    return True

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """
    Get the database URL from Flask app configuration.
    
    This function creates a Flask app instance and retrieves the database URL
    from the app configuration, allowing Alembic to work with the Flask app factory pattern.
    """
    # Create Flask app instance
    app = create_app()
    
    # Get database URL from app config
    with app.app_context():
        return app.config.get('SQLALCHEMY_DATABASE_URI')


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    config.set_main_option("sqlalchemy.url", url)
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Enable better autogenerate detection for offline mode
        compare_type=True,              # Detect type changes (e.g., String(50) -> String(100))
        compare_server_default=True,    # Detect default value changes
        include_object=include_object   # Use filter function
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get database URL from Flask app
    url = get_url()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Enable better autogenerate detection
            compare_type=True,          # Detect type changes
            compare_server_default=True,  # Detect default value changes
            render_as_batch=False,     # Use ALTER TABLE for MySQL
            include_object=include_object  # Optional: filter objects
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

