"""
Alembic environment configuration.

Reads DATABASE_URL from the environment (overriding the alembic.ini placeholder)
and targets the SQLAlchemy Base.metadata from backend.db.models.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# Import the declarative Base so that all model metadata is registered.
from backend.db.models import Base  # noqa: F401 — side-effect: populates Base.metadata

# ---------------------------------------------------------------------------
# Alembic Config object (gives access to values in alembic.ini)
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging from alembic.ini [loggers] section, if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Target metadata — tells autogenerate which tables to compare against
# ---------------------------------------------------------------------------
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_database_url() -> str:
    """
    Resolve the database URL.

    Priority:
      1. DATABASE_URL environment variable (set in docker-compose / CI)
      2. sqlalchemy.url from alembic.ini (fallback — usually the %(DATABASE_URL)s placeholder)

    Raises RuntimeError if neither is available.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    # Try the ini value (may be the raw placeholder string)
    ini_url: str | None = config.get_main_option("sqlalchemy.url")
    if ini_url and "%(DATABASE_URL)s" not in ini_url:
        return ini_url

    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Export the environment variable before running alembic commands."
    )


# ---------------------------------------------------------------------------
# Offline migrations (generate SQL without a live DB connection)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Emit migration SQL to stdout without connecting to the database.
    Useful for generating SQL scripts to review or apply manually.
    """
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (connect to DB and apply migrations directly)
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    """
    Run migrations against a live database connection.
    Uses NullPool to avoid connection leaks in short-lived alembic processes.
    """
    url = _get_database_url()

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
