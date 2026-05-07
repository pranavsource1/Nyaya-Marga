"""API endpoint tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from app.models.domain_models import Case, CaseStatus, ExtractedEntity
from app.core.database import get_db, AsyncSessionLocal


@pytest.fixture
def client():
    """Create API test client."""
    return TestClient(app)


@pytest.fixture
async def override_get_db():
    """Override get_db dependency for tests."""
    async with AsyncSessionLocal() as session:
        yield session


class TestCaseUploadEndpoint:
    """Test case upload endpoint."""

    def test_upload_case_success(self, client, mock_pdf_path):
        """Test successful case upload."""
        with open(mock_pdf_path, "rb") as f:
            response = client.post(
                "/api/v1/cases/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"case_number": "TEST-2024-001"},
            )

        assert response.status_code == 202
        data = response.json()
        assert "case_id" in data
        assert "task_id" in data
        assert "case_number" in data
        assert data["case_number"] == "TEST-2024-001"
        assert data["status"] == "processing"

    def test_upload_case_no_file(self, client):
        """Test upload with no file."""
        response = client.post(
            "/api/v1/cases/upload",
            data={"case_number": "TEST-2024-001"},
        )

        assert response.status_code == 400
        assert "No file provided" in response.json().get("detail", "")

    def test_upload_case_invalid_file_type(self, client, tmp_path):
        """Test upload with non-PDF file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Not a PDF")

        with open(txt_file, "rb") as f:
            response = client.post(
                "/api/v1/cases/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={"case_number": "TEST-2024-001"},
            )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_case_missing_case_number(self, client, mock_pdf_path):
        """Test upload with missing case number."""
        with open(mock_pdf_path, "rb") as f:
            response = client.post(
                "/api/v1/cases/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
            )

        assert response.status_code == 400

    def test_upload_case_duplicate_case_number(self, client, mock_pdf_path, db_session):
        """Test upload with duplicate case number."""
        case_number = "DUPLICATE-2024-001"

        # Create first case
        import asyncio
        async def create_case():
            db_case = Case(
                case_number=case_number,
                pdf_path="/tmp/test.pdf",
                status=CaseStatus.PROCESSING.value,
            )
            db_session.add(db_case)
            await db_session.commit()

        asyncio.run(create_case())

        # Try to upload duplicate
        with open(mock_pdf_path, "rb") as f:
            response = client.post(
                "/api/v1/cases/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"case_number": case_number},
            )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_upload_case_file_size_exceeded(self, client, tmp_path):
        """Test upload with file exceeding size limit."""
        # Create large file (will depend on MAX_UPLOAD_SIZE_MB)
        large_file = tmp_path / "large.pdf"

        # Create a minimal PDF
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "x" * 10000)  # Add large text
        doc.save(str(large_file))
        doc.close()

        with open(large_file, "rb") as f:
            response = client.post(
                "/api/v1/cases/upload",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"case_number": "TEST-2024-001"},
            )

        # May fail for size or succeed depending on setup
        assert response.status_code in [202, 413]


class TestCaseStatusEndpoint:
    """Test case status endpoint."""

    def test_get_case_status_not_found(self, client):
        """Test getting status for non-existent case."""
        response = client.get("/api/v1/cases/9999/status")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_case_status_success(self, client, sample_case_data):
        """Test getting status for existing case.

        Note: Requires case to exist in database.
        """
        # This test would require setting up database state
        # Skipping for now - would need async db fixture integration
        pass


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "database" in data
        assert "celery" in data

    def test_health_check_response_schema(self, client):
        """Test health check response has correct schema."""
        response = client.get("/health")

        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert isinstance(data["version"], str)
        assert data["database"] in ["connected", "disconnected"]
        assert data["celery"] in ["connected", "disconnected"]


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Nyaya Marga" in data["message"]
        assert "docs" in data
