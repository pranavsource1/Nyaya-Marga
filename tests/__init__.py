"""Test configuration and shared fixtures."""
import pytest
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Async event loop for pytest
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    # Use test database
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5432/nyaya_test"
    )

    engine = create_async_engine(test_db_url, echo=False)

    # Create tables
    from app.core.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

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

    # Create a minimal PDF with simple text
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test Case Number: CASE-2024-001")
    page.insert_text((50, 100), "Plaintiff: John Smith")
    page.insert_text((50, 150), "Defendant: ABC Corporation")
    doc.save(str(pdf_file))
    doc.close()

    return str(pdf_file)


@pytest.fixture
def mock_scanned_pdf_path(tmp_path):
    """Create a PDF that needs OCR (image-based)."""
    from PIL import Image, ImageDraw
    import fitz

    pdf_file = tmp_path / "scanned.pdf"

    # Create image with text
    img = Image.new('RGB', (612, 792), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "SCANNED LEGAL DOCUMENT", fill='black')
    draw.text((50, 100), "Case Name: Smith v. Corp", fill='black')

    # Convert image to PDF
    doc = fitz.open()
    page = doc.new_page()
    # Insert PIL image into PDF
    from io import BytesIO
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    pixmap = fitz.Pixmap(img)
    page.insert_image(page.rect, pixmap=pixmap)

    doc.save(str(pdf_file))
    doc.close()

    return str(pdf_file)


@pytest.fixture
def sample_case_data():
    """Sample case data for testing."""
    return {
        "case_number": "TEST-2024-001",
        "pdf_path": "/tmp/test.pdf",
    }
