"""
alembic/env.py
--------------
Alembic migration environment.

Key design choices:
1. URL is read from POSTGRES_URI env var (never hardcoded)
2. Uses synchronous psycopg2-compatible URL for migrations
   (Alembic does not support asyncpg natively — we swap the driver scheme)
3. Autogenerate is enabled — Alembic detects model changes automatically
4. All models imported via app.db so autogenerate sees every table
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Add backend/ to sys.path so app.* imports work ───────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Load all models so autogenerate sees every table ─────────────────────────
import app.db  # noqa: F401 — side effect: registers all ORM models with Base.metadata

from app.db.base import Base
from app.core.config import settings

# Alembic Config object (access to alembic.ini values)
config = context.config

# Logging configuration from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def get_sync_url() -> str:
    """
    Convert the asyncpg URL to a synchronous psycopg2 URL for Alembic.
    asyncpg:  postgresql+asyncpg://user:pass@host:port/db
    psycopg2: postgresql+psycopg2://user:pass@host:port/db  (or just postgresql://)
    """
    uri = settings.POSTGRES_URI
    # Replace asyncpg driver with psycopg2 for synchronous operations
    return uri.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (generate SQL without connecting).
    Useful for generating migration scripts for review.
    """
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,          # Detect column type changes
        compare_server_default=True, # Detect server_default changes
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (execute directly against the database).
    """
    # Override sqlalchemy.url from alembic.ini with our dynamic URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_sync_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool for migrations — no connection pooling needed
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
