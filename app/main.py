"""FastAPI application factory and initialization.

Sets up the FastAPI app with middleware, routes, and startup/shutdown handlers.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.routes import router
from app.api.auth import router as auth_router
from app.api.verification import router as verification_router
from app.api.dashboard import router as dashboard_router
from app.api.webhooks import router as webhooks_router
from app.api.search import router as search_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: startup and shutdown.

    Startup:
    - Initialize database tables
    - Log startup info

    Shutdown:
    - Close database connections
    """
    logger.info("=" * 60)
    logger.info(f"Starting {settings.api_title} v{settings.api_version}")
    logger.info(f"Debug: {settings.debug}")
    logger.info("=" * 60)

    await init_db()
    logger.info("Database initialized")

    yield

    logger.info("Shutting down application...")
    await close_db()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI instance
    """
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description="Phase 2: Intelligent Ingestion Engine for legal document processing",
        lifespan=lifespan,
    )

    # CORS middleware for Phase 4 Next.js frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:8000", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(verification_router)
    app.include_router(dashboard_router)
    app.include_router(webhooks_router)
    app.include_router(search_router)

    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint."""
        return {
            "message": "Nyaya Marga - Phase 2: Intelligent Ingestion Engine",
            "version": settings.api_version,
            "docs": "/docs",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )
