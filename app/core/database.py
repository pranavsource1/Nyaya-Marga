"""Async database configuration using SQLAlchemy 2.0."""
import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from .config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    poolclass=NullPool,  # Recommended for async connections
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency injection for database sessions."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Initialize database tables and SQL rules for immutability."""

    # Step 1: Enable required extensions
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto" CASCADE'))

    # Step 2: Try optional pgvector extension (separate transaction)
    try:
        async with engine.begin() as conn:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector" CASCADE'))
            logger.info("pgvector extension enabled")
    except Exception as e:
        logger.warning(f"pgvector extension not available (optional): {e}")

    # Step 3: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Step 4: Create SQL rules for immutability (audit_log is INSERT-only)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE OR REPLACE RULE audit_log_no_update AS
                ON UPDATE TO audit_log DO INSTEAD NOTHING
            """))
            await conn.execute(text("""
                CREATE OR REPLACE RULE audit_log_no_delete AS
                ON DELETE TO audit_log DO INSTEAD NOTHING
            """))
            logger.info("Audit log immutability rules created")
    except Exception as e:
        logger.warning(f"Could not create audit log rules: {e}")


async def close_db():
    """Close database connections."""
    await engine.dispose()
