"""Pytest configuration and fixtures."""
import os
import sys
import pytest
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Add parent (root) to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Pytest markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "asyncio: marks tests as async")


# Load test database URL from env or use default
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/nyaya_test"
)

# Disable async warnings in tests
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


# Async event loop
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5432/nyaya_test"
    )

    engine = create_async_engine(test_db_url, echo=False)

    # Create tables
    try:
        from app.core.database import Base
        # Already on parent path, imports should work
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Warning: Could not create database tables: {e}")

    yield engine

    # Cleanup
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        pass

    await engine.dispose()


@pytest.fixture
async def db_session(test_db):
    """Create test database session."""
    async_session = async_sessionmaker(test_db, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_pdf_path(tmp_path):
    """Create a temporary PDF file for testing."""
    pdf_file = tmp_path / "test.pdf"

    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Test Case Number: CASE-2024-001")
        page.insert_text((50, 100), "Plaintiff: John Smith")
        page.insert_text((50, 150), "Defendant: ABC Corporation")
        doc.save(str(pdf_file))
        doc.close()
    except Exception as e:
        print(f"Warning: Could not create mock PDF: {e}")
        # Create a minimal text file as fallback
        pdf_file.write_text("Mock PDF content")

    return str(pdf_file)


@pytest.fixture
def mock_scanned_pdf_path(tmp_path):
    """Create a PDF that needs OCR (image-based)."""
    pdf_file = tmp_path / "scanned.pdf"

    try:
        from PIL import Image, ImageDraw
        import fitz

        # Create image with text
        img = Image.new('RGB', (612, 792), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "SCANNED LEGAL DOCUMENT", fill='black')
        draw.text((50, 100), "Case Name: Smith v. Corp", fill='black')

        # Convert image to PDF
        doc = fitz.open()
        page = doc.new_page()
        pix = fitz.Pixmap(img)
        page.insert_image(page.rect, pixmap=pix)
        doc.save(str(pdf_file))
        doc.close()
    except Exception as e:
        print(f"Warning: Could not create scanned PDF: {e}")
        pdf_file.write_text("Mock scanned PDF")

    return str(pdf_file)


@pytest.fixture
def sample_case_data():
    """Sample case data for testing."""
    return {
        "case_number": "TEST-2024-001",
        "pdf_path": "/tmp/test.pdf",
    }
