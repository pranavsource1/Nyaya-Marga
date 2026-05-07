"""PDF extraction service with PyMuPDF and OCR fallback.

Implements hybrid extraction strategy:
1. First attempt: PyMuPDF text extraction with coordinates
2. Fallback: OCR via pytesseract if insufficient text detected
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import io

logger = logging.getLogger(__name__)


class BoundingBox:
    """Immutable bounding box data class."""
    def __init__(self, page: int, x0: float, y0: float, x1: float, y1: float):
        self.page = page
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "page": self.page,
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
        }


class ExtractedWord:
    """Represents a word extracted from PDF with spatial coordinates."""
    def __init__(
        self,
        text: str,
        bbox: BoundingBox,
        confidence: Optional[float] = None,
    ):
        self.text = text
        self.bbox = bbox
        self.confidence = confidence or 1.0  # Default high confidence for direct extraction

    def __repr__(self) -> str:
        return f"ExtractedWord(text='{self.text}', page={self.bbox.page})"


class PageContent:
    """Container for all content extracted from a single PDF page."""
    def __init__(self, page_num: int, raw_text: str, words: List[ExtractedWord], method: str):
        self.page_num = page_num
        self.raw_text = raw_text
        self.words = words
        self.method = method  # "pdfminer" or "ocr"
        self.word_count = len(words)

    def __repr__(self) -> str:
        return f"PageContent(page={self.page_num}, words={self.word_count}, method={self.method})"


class PDFService:
    """Service for extracting text and coordinates from PDF documents.

    Uses a hybrid approach:
    - Primary: PyMuPDF for direct text + bounding box extraction
    - Fallback: OCR when text extraction yields insufficient words
    """

    OCR_THRESHOLD = 10  # Minimum word count before trying OCR
    TESSERACT_CONFIG = "--psm 6"  # PSM 6: assume single block of text

    def __init__(self, pdf_path: str):
        """Initialize PDF service with file path.

        Args:
            pdf_path: Path to PDF file on disk

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            fitz.FileError: If file is not a valid PDF
        """
        self.pdf_path = pdf_path
        self.document = None
        self._initialize_document()

    def _initialize_document(self) -> None:
        """Open and validate PDF document."""
        try:
            self.document = fitz.open(self.pdf_path)
            logger.info(
                f"Opened PDF: {self.pdf_path} with {self.document.page_count} pages"
            )
        except FileNotFoundError:
            logger.error(f"PDF file not found: {self.pdf_path}")
            raise
        except Exception as e:
            logger.error(f"Invalid PDF file: {self.pdf_path} - {e}")
            raise

    def extract_page(self, page_num: int) -> PageContent:
        """Extract text and coordinates from a single page.

        Strategy:
        1. Try PyMuPDF text extraction
        2. If word count < OCR_THRESHOLD, fall back to OCR

        Args:
            page_num: Zero-indexed page number

        Returns:
            PageContent with words and metadata

        Raises:
            ValueError: If page number out of range
        """
        if page_num < 0 or page_num >= self.document.page_count:
            raise ValueError(
                f"Page {page_num} out of range (0-{self.document.page_count - 1})"
            )

        # Try primary extraction method (PyMuPDF)
        page_content = self._extract_via_pymupdf(page_num)

        # Fall back to OCR if insufficient text
        if page_content.word_count < self.OCR_THRESHOLD:
            logger.info(
                f"Page {page_num}: Only {page_content.word_count} words found. "
                f"Attempting OCR fallback..."
            )
            page_content = self._extract_via_ocr(page_num)

        return page_content

    def _extract_via_pymupdf(self, page_num: int) -> PageContent:
        """Extract using PyMuPDF's page.get_text("words") method.

        Returns sparse words list with high confidence.

        Args:
            page_num: Zero-indexed page number

        Returns:
            PageContent using PyMuPDF extraction
        """
        try:
            page = self.document[page_num]
            # get_text("words") returns list of (x0, y0, x1, y1, text, block_num, line_num, word_num)
            words_data = page.get_text("words")
            raw_text = page.get_text("text")

            extracted_words: List[ExtractedWord] = []
            for word_info in words_data:
                x0, y0, x1, y1, text, *_ = word_info
                bbox = BoundingBox(page_num, float(x0), float(y0), float(x1), float(y1))
                extracted_words.append(ExtractedWord(text, bbox, confidence=1.0))

            return PageContent(
                page_num=page_num,
                raw_text=raw_text,
                words=extracted_words,
                method="pdfminer",
            )
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed for page {page_num}: {e}")
            return PageContent(page_num, "", [], "pdfminer_failed")

    def _extract_via_ocr(self, page_num: int) -> PageContent:
        """Fall back to OCR extraction using pytesseract.

        Converts page to image, runs OCR, and maps coordinates from OCR output.

        Args:
            page_num: Zero-indexed page number

        Returns:
            PageContent using OCR extraction

        Raises:
            RuntimeError: If OCR processing fails
        """
        try:
            # Convert PDF page to PIL Image
            images = convert_from_path(self.pdf_path, first_page=page_num + 1, last_page=page_num + 1)
            if not images:
                logger.error(f"Failed to convert page {page_num} to image")
                return PageContent(page_num, "", [], "ocr_failed")

            image = images[0]

            # Run pytesseract.image_to_data to get coordinates
            ocr_data = pytesseract.image_to_data(
                image, config=self.TESSERACT_CONFIG, output_type=pytesseract.Output.DICT
            )

            extracted_words: List[ExtractedWord] = []
            for idx in range(len(ocr_data["text"])):
                text = ocr_data["text"][idx].strip()
                if not text:  # Skip empty results
                    continue

                confidence = int(ocr_data["conf"][idx]) / 100.0
                x0 = int(ocr_data["left"][idx])
                y0 = int(ocr_data["top"][idx])
                x1 = x0 + int(ocr_data["width"][idx])
                y1 = y0 + int(ocr_data["height"][idx])

                bbox = BoundingBox(page_num, float(x0), float(y0), float(x1), float(y1))
                extracted_words.append(ExtractedWord(text, bbox, confidence=confidence))

            # Get raw text for metadata
            raw_text = pytesseract.image_to_string(image, config=self.TESSERACT_CONFIG)

            return PageContent(
                page_num=page_num,
                raw_text=raw_text,
                words=extracted_words,
                method="ocr",
            )
        except Exception as e:
            logger.error(f"OCR extraction failed for page {page_num}: {e}")
            raise RuntimeError(f"OCR extraction failed: {e}") from e

    def extract_all_pages(self) -> List[PageContent]:
        """Extract text from all pages in document.

        Returns:
            List of PageContent objects (one per page)
        """
        pages = []
        for page_num in range(self.document.page_count):
            try:
                page_content = self.extract_page(page_num)
                pages.append(page_content)
                logger.debug(f"Extracted page {page_num}: {page_content}")
            except Exception as e:
                logger.error(f"Error extracting page {page_num}: {e}")
                # Continue with other pages, but log the error
                pages.append(PageContent(page_num, "", [], "failed"))

        return pages

    def close(self) -> None:
        """Close the PDF document and release resources."""
        if self.document:
            self.document.close()
            self.document = None
            logger.info(f"Closed PDF: {self.pdf_path}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
