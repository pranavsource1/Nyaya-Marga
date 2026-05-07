"""Dependency injection for FastAPI routes.

Provides database session and Celery task queue access to route handlers.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for route handlers.

    FastAPI dependency that yields AsyncSession for async database operations.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession instance

    Raises:
        sqlalchemy.exc.SQLAlchemyError: Database connection errors
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
