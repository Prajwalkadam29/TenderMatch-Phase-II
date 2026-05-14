"""
postgres.py
-----------
SQLAlchemy async engine and session factory for PostgreSQL.

Architecture:
- Uses asyncpg driver (fastest PostgreSQL async driver for Python)
- Connection pool: configurable pool_size + max_overflow
- Sessions are managed via AsyncSession + async context manager
- Alembic uses a SYNCHRONOUS URL (psycopg2-style) for migrations only

Usage in FastAPI route:
    async with get_pg_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

Usage as FastAPI dependency:
    async def my_route(session: AsyncSession = Depends(get_pg_db)):
        ...
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Module-level engine and session factory ────────────────────────────────────
# Initialised by init_postgres() at application startup (lifespan).
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_postgres() -> None:
    """
    Create the SQLAlchemy async engine and session factory.
    Called once during FastAPI lifespan startup.
    """
    global _engine, _session_factory

    logger.info("[Postgres] Initializing async engine...")

    _engine = create_async_engine(
        settings.POSTGRES_URI,
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_overflow=settings.POSTGRES_MAX_OVERFLOW,
        pool_pre_ping=True,        # Re-validate connections before handing out
        pool_recycle=3600,         # Recycle connections every 1 hour
        echo=(settings.ENVIRONMENT == "development"),  # SQL logging in dev only
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,    # Don't expire objects after commit (avoids lazy-load issues)
        autoflush=False,
        autocommit=False,
    )

    # Verify connectivity
    async with _engine.connect() as conn:
        from sqlalchemy import text
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar()
        logger.info("[Postgres] Connected. Server: %s", version)

    logger.info("[Postgres] Engine and session factory ready.")


async def close_postgres() -> None:
    """Dispose the engine and close all connections. Called at app shutdown."""
    global _engine
    if _engine:
        logger.info("[Postgres] Closing connection pool...")
        await _engine.dispose()
        _engine = None
        logger.info("[Postgres] Connection pool closed.")


def get_engine() -> AsyncEngine:
    """Return the module-level engine. Raises if not initialised."""
    if _engine is None:
        raise RuntimeError("PostgreSQL engine not initialised. Call init_postgres() first.")
    return _engine


@asynccontextmanager
async def get_pg_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that provides a database session.
    Commits on success, rolls back on exception.

    Usage:
        async with get_pg_session() as session:
            await session.execute(...)
    """
    if _session_factory is None:
        raise RuntimeError("PostgreSQL session factory not initialised.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_pg_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a PostgreSQL session.

    Usage:
        async def my_route(db: AsyncSession = Depends(get_pg_db)):
            ...
    """
    if _session_factory is None:
        raise RuntimeError("PostgreSQL session factory not initialised.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
