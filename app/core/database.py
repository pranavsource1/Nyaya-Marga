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

import ssl

# Convert standard postgres URLs to asyncpg to prevent 'psycopg2 is not async' errors
db_url = settings.database_url
if db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

# Check if we're connecting to Supabase which requires SSL
connect_args = {}
if db_url and "supabase.co" in db_url:
    # Supabase requires SSL, but sometimes asyncpg needs explicit SSL context or "require"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context

engine = create_async_engine(
    db_url,
    echo=settings.database_echo,
    poolclass=NullPool,  # Recommended for async connections
    connect_args=connect_args,
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
