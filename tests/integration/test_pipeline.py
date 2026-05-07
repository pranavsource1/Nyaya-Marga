"""Integration tests for Celery task orchestration."""
import pytest
from sqlalchemy import select

from app.models.domain_models import Case, CaseStatus, ExtractedEntity
from app.worker.tasks import _stage_pdf_extraction, _stage_nlp_analysis, _bulk_insert_entities


class TestPDFExtractionStage:
    """Test PDF extraction stage of Celery pipeline."""

    @pytest.mark.asyncio
    async def test_pdf_extraction_stage(self, mock_pdf_path, db_session):
        """Test PDF extraction stage returns data."""
        result = await _stage_pdf_extraction(case_id=1, pdf_path=mock_pdf_path, session=db_session)

        assert isinstance(result, list)
        assert len(result) > 0

        # Check page structure
        for page in result:
            assert "page_num" in page
            assert "raw_text" in page
            assert "method" in page
            assert "words" in page
            assert isinstance(page["words"], list)

    @pytest.mark.asyncio
    async def test_pdf_extraction_invalid_path(self, db_session):
        """Test PDF extraction with invalid path."""
        with pytest.raises(RuntimeError):
            await _stage_pdf_extraction(case_id=1, pdf_path="/invalid/path.pdf", session=db_session)

    @pytest.mark.asyncio
    async def test_pdf_extraction_word_coordinates(self, mock_pdf_path, db_session):
        """Test that extracted words have coordinates."""
        result = await _stage_pdf_extraction(case_id=1, pdf_path=mock_pdf_path, session=db_session)

        for page in result:
            for word in page["words"]:
                assert "text" in word
                assert "bbox" in word
                assert "confidence" in word

                bbox = word["bbox"]
                assert "page" in bbox
                assert "x0" in bbox
                assert "y0" in bbox
                assert "x1" in bbox
                assert "y1" in bbox


class TestBulkInsertEntities:
    """Test bulk entity insertion."""

    @pytest.mark.asyncio
    async def test_bulk_insert_single_batch(self, db_session):
        """Test bulk insert with single batch."""
        case_id = 1
        entities = [
            (
                case_id,
                {
                    "entity_type": "PERSON",
                    "extracted_text": "John Smith",
                    "confidence_score": 0.95,
                    "requires_review": False,
                    "bounding_box_coords": {"page": 0, "x0": 100, "y0": 200, "x1": 250, "y1": 220},
                },
            ),
            (
                case_id,
                {
                    "entity_type": "LOCATION",
                    "extracted_text": "New York",
                    "confidence_score": 0.88,
                    "requires_review": False,
                    "bounding_box_coords": None,
                },
            ),
        ]

        count = await _bulk_insert_entities(case_id, entities, db_session)

        assert count == 2

        # Verify in database
        result = await db_session.execute(select(ExtractedEntity).where(ExtractedEntity.case_id == case_id))
        db_entities = result.scalars().all()
        assert len(db_entities) == 2

    @pytest.mark.asyncio
    async def test_bulk_insert_multiple_batches(self, db_session):
        """Test bulk insert with multiple batches."""
        case_id = 1
        # Create 250 entities (will span 3 batches of 100)
        entities = [
            (
                case_id,
                {
                    "entity_type": "PERSON",
                    "extracted_text": f"Person_{i}",
                    "confidence_score": 0.90 + (i % 10) * 0.01,
                    "requires_review": False,
                    "bounding_box_coords": None,
                },
            )
            for i in range(250)
        ]

        count = await _bulk_insert_entities(case_id, entities, db_session)

        assert count == 250

        # Verify all in database
        result = await db_session.execute(select(ExtractedEntity).where(ExtractedEntity.case_id == case_id))
        db_entities = result.scalars().all()
        assert len(db_entities) == 250

    @pytest.mark.asyncio
    async def test_bulk_insert_empty_list(self, db_session):
        """Test bulk insert with empty list."""
        count = await _bulk_insert_entities(case_id=1, entities=[], session=db_session)
        assert count == 0

    @pytest.mark.asyncio
    async def test_bulk_insert_with_review_flags(self, db_session):
        """Test that requires_review flags are stored."""
        case_id = 1
        entities = [
            (
                case_id,
                {
                    "entity_type": "PERSON",
                    "extracted_text": "Alice",
                    "confidence_score": 0.95,
                    "requires_review": False,
                },
            ),
            (
                case_id,
                {
                    "entity_type": "PERSON",
                    "extracted_text": "Bob",
                    "confidence_score": 0.60,  # Below 0.75 threshold
                    "requires_review": True,
                },
            ),
        ]

        await _bulk_insert_entities(case_id, entities, db_session)

        result = await db_session.execute(select(ExtractedEntity).where(ExtractedEntity.case_id == case_id))
        db_entities = result.scalars().all()

        # Verify flags
        alice = next((e for e in db_entities if e.extracted_text == "Alice"), None)
        bob = next((e for e in db_entities if e.extracted_text == "Bob"), None)

        assert alice is not None
        assert alice.requires_review is False
        assert bob is not None
        assert bob.requires_review is True
