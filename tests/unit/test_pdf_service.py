"""Unit tests for PDF extraction service."""
import pytest
import os
from app.services.pdf_service import PDFService, BoundingBox, ExtractedWord, PageContent


class TestBoundingBox:
    """Test BoundingBox data class."""

    def test_bbox_creation(self):
        """Test BoundingBox initialization."""
        bbox = BoundingBox(0, 100.5, 200.3, 250.7, 220.1)
        assert bbox.page == 0
        assert bbox.x0 == 100.5
        assert bbox.y0 == 200.3
        assert bbox.x1 == 250.7
        assert bbox.y1 == 220.1

    def test_bbox_to_dict(self):
        """Test BoundingBox serialization."""
        bbox = BoundingBox(1, 10.0, 20.0, 30.0, 40.0)
        result = bbox.to_dict()

        assert result == {
            "page": 1,
            "x0": 10.0,
            "y0": 20.0,
            "x1": 30.0,
            "y1": 40.0,
        }


class TestExtractedWord:
    """Test ExtractedWord data class."""

    def test_word_creation(self):
        """Test ExtractedWord initialization."""
        bbox = BoundingBox(0, 100.0, 200.0, 150.0, 220.0)
        word = ExtractedWord("Test", bbox, confidence=0.95)

        assert word.text == "Test"
        assert word.bbox == bbox
        assert word.confidence == 0.95

    def test_word_default_confidence(self):
        """Test ExtractedWord default confidence."""
        bbox = BoundingBox(0, 100.0, 200.0, 150.0, 220.0)
        word = ExtractedWord("Test", bbox)

        assert word.confidence == 1.0


class TestPDFService:
    """Test PDF extraction service."""

    def test_pdf_initialization(self, mock_pdf_path):
        """Test PDF service initialization."""
        service = PDFService(mock_pdf_path)
        assert service.pdf_path == mock_pdf_path
        assert service.document is not None
        assert service.document.page_count > 0
        service.close()

    def test_pdf_not_found(self):
        """Test PDF service with non-existent file."""
        with pytest.raises((FileNotFoundError, Exception)):
            PDFService("/nonexistent/path/file.pdf")

    def test_invalid_pdf(self, tmp_path):
        """Test PDF service with invalid PDF file."""
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("This is not a PDF")

        with pytest.raises(Exception):  # fitz.FileError
            PDFService(str(invalid_pdf))

    def test_extract_page_valid(self, mock_pdf_path):
        """Test extracting from valid PDF page."""
        service = PDFService(mock_pdf_path)
        page_content = service.extract_page(0)

        assert isinstance(page_content, PageContent)
        assert page_content.page_num == 0
        assert len(page_content.words) > 0
        assert page_content.word_count > 0

        service.close()

    def test_extract_page_out_of_range(self, mock_pdf_path):
        """Test extracting from out-of-range page."""
        service = PDFService(mock_pdf_path)

        with pytest.raises(ValueError):
            service.extract_page(999)

        service.close()

    def test_extract_all_pages(self, mock_pdf_path):
        """Test extracting all pages."""
        service = PDFService(mock_pdf_path)
        pages = service.extract_all_pages()

        assert len(pages) > 0
        assert all(isinstance(p, PageContent) for p in pages)
        assert all(p.page_num == i for i, p in enumerate(pages))

        service.close()

    def test_context_manager(self, mock_pdf_path):
        """Test PDF service context manager."""
        with PDFService(mock_pdf_path) as service:
            assert service.document is not None
            pages = service.extract_all_pages()
            assert len(pages) > 0

        assert service.document is None

    def test_extract_words_have_coordinates(self, mock_pdf_path):
        """Test that extracted words have valid coordinates."""
        service = PDFService(mock_pdf_path)
        page = service.extract_page(0)

        for word in page.words:
            assert word.bbox.page >= 0
            assert word.bbox.x0 >= 0
            assert word.bbox.y0 >= 0
            assert word.bbox.x1 >= word.bbox.x0
            assert word.bbox.y1 >= word.bbox.y0

        service.close()

    def test_extract_word_confidence_scores(self, mock_pdf_path):
        """Test that extracted words have confidence scores."""
        service = PDFService(mock_pdf_path)
        page = service.extract_page(0)

        for word in page.words:
            assert 0.0 <= word.confidence <= 1.0

        service.close()

    def test_extraction_method_tracking(self, mock_pdf_path):
        """Test that extraction method is tracked."""
        service = PDFService(mock_pdf_path)
        page = service.extract_page(0)

        assert page.method in ["pdfminer", "ocr", "pdfminer_failed", "ocr_failed"]

        service.close()

    def test_extract_multiple_pages(self, mock_pdf_path):
        """Test extracting multiple pages sequentially."""
        service = PDFService(mock_pdf_path)

        # Extract pages individually
        page0 = service.extract_page(0)
        assert page0.page_num == 0

        # Extract all and compare
        all_pages = service.extract_all_pages()
        assert all_pages[0].page_num == page0.page_num
        assert len(all_pages[0].words) == len(page0.words)

        service.close()
