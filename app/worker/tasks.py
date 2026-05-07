"""Celery worker tasks for orchestrating the intelligent ingestion pipeline.

Pipeline flow:
1. processing: Receive task, extract text from PDF
2. pending_nlp: Run NLP on extracted text
3. pending_review: Store results, await manual verification
4. verified/failed: Final state

Phase 3 additions:
- generate_action_plan_task: Generate administrative action plan using LLM + RAG

Uses database transactions and bulk inserts for efficiency.
"""
import logging
from typing import List, Dict, Any
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.domain_models import Case, ExtractedEntity, CaseStatus
from app.services.pdf_service import PDFService, ExtractedWord, BoundingBox
from app.services.nlp_service import NLPService
from app.services.llm_service import ActionPlanGenerator

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2)
def process_case(self, case_id: Any, pdf_path: str) -> Dict[str, Any]:
    """Orchestrate the complete case processing pipeline.

    Manages state transitions and coordinates PDF extraction and NLP analysis.

    Pipeline:
    1. processing -> pending_nlp (PDF extraction)
    2. pending_nlp -> pending_review (NLP analysis)
    3. pending_review -> verified (success)
    4. Any stage -> failed (on error)

    Args:
        case_id: Database Case ID
        pdf_path: Path to PDF file on disk

    Returns:
        Dict with processing result and entity count

    Raises:
        Handled gracefully with retry logic and status update
    """
    logger.info(f"Starting process_case task for case_id={case_id}, pdf_path={pdf_path}")

    try:
        # Stage 1: PDF Extraction
        result = asyncio.run(_process_case_async(case_id, pdf_path))
        return result
    except Exception as e:
        logger.error(f"Process task failed for case_id={case_id}: {e}", exc_info=True)

        # Update case status to failed
        asyncio.run(_update_case_status_async(case_id, CaseStatus.FAILED, str(e)))

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


async def _process_case_async(case_id: Any, pdf_path: str) -> Dict[str, Any]:
    """Async implementation of case processing pipeline.

    Args:
        case_id: Database Case ID
        pdf_path: Path to PDF file

    Returns:
        Processing result dictionary
    """
    async with AsyncSessionLocal() as session:
        # Verify case exists
        case = await session.get(Case, case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found in database")

        logger.info(f"Processing case {case.case_number} (ID: {case_id})")

        # Stage 1: PDF Extraction
        await _update_case_status_async(case_id, CaseStatus.PROCESSING)
        pdf_extraction_result = await _stage_pdf_extraction(case_id, pdf_path, session)

        # Stage 2: NLP Analysis
        await _update_case_status_async(case_id, CaseStatus.PENDING_NLP)
        entity_count = await _stage_nlp_analysis(
            case_id, pdf_extraction_result, session
        )

        # Stage 3: Mark for review
        await _update_case_status_async(case_id, CaseStatus.PENDING_REVIEW)

        # Stage 4: Auto-generate action plan via NVIDIA NIM
        try:
            logger.info(f"Stage 4: Auto-generating action plan for case_id={case_id}")
            generate_action_plan_task.delay(str(case_id))
            logger.info(f"Dispatched action plan generation task for case {case.case_number}")
        except Exception as ap_err:
            logger.warning(f"Failed to auto-dispatch action plan generation: {ap_err}")

        logger.info(
            f"Case {case.case_number} processed successfully. "
            f"Extracted {entity_count} entities."
        )

        return {
            "case_id": case_id,
            "case_number": case.case_number,
            "status": CaseStatus.PENDING_REVIEW.value,
            "entity_count": entity_count,
        }


async def _stage_pdf_extraction(
    case_id: int, pdf_path: str, session: AsyncSession
) -> List[Dict[str, Any]]:
    """Stage 1: Extract text and coordinates from PDF.

    Args:
        case_id: Database Case ID
        pdf_path: Path to PDF file
        session: Database session

    Returns:
        List of page content dicts with words and coordinates

    Raises:
        RuntimeError: If PDF extraction fails completely
    """
    logger.info(f"Stage 1: PDF extraction starting for case_id={case_id}")

    try:
        pdf_service = PDFService(pdf_path)
        pages = pdf_service.extract_all_pages()
        pdf_service.close()

        if not pages:
            raise RuntimeError("No pages extracted from PDF")

        # Convert page content to serializable format
        page_data = []
        for page in pages:
            page_dict = {
                "page_num": page.page_num,
                "raw_text": page.raw_text,
                "method": page.method,
                "words": [
                    {
                        "text": w.text,
                        "bbox": w.bbox.to_dict(),
                        "confidence": w.confidence,
                    }
                    for w in page.words
                ],
            }
            page_data.append(page_dict)

        logger.info(
            f"PDF extraction complete: {len(pages)} pages, "
            f"{sum(len(p['words']) for p in page_data)} total words"
        )
        return page_data

    except Exception as e:
        logger.error(f"PDF extraction failed for case_id={case_id}: {e}", exc_info=True)
        raise RuntimeError(f"PDF extraction failed: {e}") from e


async def _stage_nlp_analysis(
    case_id: int, page_data: List[Dict[str, Any]], session: AsyncSession
) -> int:
    """Stage 2: Run NLP on extracted text and store entities.

    Uses bulk insert for efficiency.

    Args:
        case_id: Database Case ID
        page_data: Output from PDF extraction stage
        session: Database session

    Returns:
        Number of entities successfully extracted and stored

    Raises:
        RuntimeError: If NLP analysis fails
    """
    logger.info(f"Stage 2: NLP analysis starting for case_id={case_id}")

    try:
        nlp_service = NLPService(
            model_name=settings.nlp_model_name,
            chunk_size=settings.nlp_chunk_size,
            chunk_overlap=settings.nlp_chunk_overlap,
            confidence_threshold=settings.nlp_confidence_threshold,
        )

        all_entities = []

        # Process each page
        for page_dict in page_data:
            raw_text = page_dict.get("raw_text", "")
            if not raw_text.strip():
                logger.debug(f"Skipping empty page {page_dict['page_num']}")
                continue

            # Extract entities from page text
            entities = nlp_service.extract_entities_from_text(raw_text)

            # Create ExtractedWord objects for coordinate mapping
            words_with_coords = [
                ExtractedWord(
                    w["text"],
                    BoundingBox(**w["bbox"]),
                    w["confidence"],
                )
                for w in page_dict.get("words", [])
            ]

            # Map entities to coordinates
            mapped_entities = nlp_service.map_entities_to_coordinates(
                entities, words_with_coords
            )

            for entity_dict in mapped_entities:
                all_entities.append((case_id, entity_dict))

        nlp_service.close()

        # Bulk insert entities
        entity_count = await _bulk_insert_entities(case_id, all_entities, session)

        logger.info(f"NLP analysis complete: {entity_count} entities extracted")
        return entity_count

    except Exception as e:
        logger.error(f"NLP analysis failed for case_id={case_id}: {e}", exc_info=True)
        raise RuntimeError(f"NLP analysis failed: {e}") from e


async def _bulk_insert_entities(
    case_id: int, entities: List[tuple], session: AsyncSession
) -> int:
    """Bulk insert extracted entities into database.

    Args:
        case_id: Database Case ID
        entities: List of (case_id, entity_dict) tuples
        session: Database session

    Returns:
        Number of entities inserted

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If database insert fails
    """
    logger.info(f"Bulk inserting {len(entities)} entities for case_id={case_id}")

    batch_size = 100
    total_inserted = 0

    try:
        for i in range(0, len(entities), batch_size):
            batch = entities[i : i + batch_size]
            db_entities = [
                ExtractedEntity(
                    case_id=case_id,
                    entity_type=entity_dict["entity_type"],
                    extracted_text=entity_dict["extracted_text"],
                    confidence_score=entity_dict["confidence_score"],
                    bounding_box_coords=entity_dict.get("bounding_box_coords"),
                    requires_review=entity_dict["requires_review"],
                )
                for _, entity_dict in batch
            ]

            session.add_all(db_entities)
            await session.commit()
            total_inserted += len(db_entities)
            logger.debug(f"Inserted batch of {len(db_entities)} entities")

        return total_inserted

    except Exception as e:
        await session.rollback()
        logger.error(f"Bulk insert failed: {e}", exc_info=True)
        raise


async def _update_case_status_async(
    case_id: int, status: CaseStatus, error_message: str = None
) -> None:
    """Update case status in database.

    Args:
        case_id: Database Case ID
        status: New CaseStatus
        error_message: Optional error message to store
    """
    async with AsyncSessionLocal() as session:
        case = await session.get(Case, case_id)
        if case:
            case.status = status.value
            if error_message:
                case.error_message = error_message
            await session.commit()
            logger.info(f"Case {case_id} status updated to {status.value}")


@celery_app.task(bind=True, max_retries=2)
def generate_action_plan_task(self, case_id: Any) -> Dict[str, Any]:
    """Generate administrative action plan for case using LLM + RAG.

    Orchestrates:
    1. Fetch extracted entities from database
    2. Synthesize entity summary
    3. Retrieve historical precedents via RAG
    4. Generate structured action plan via Ollama
    5. Save to Case.generated_action_plan (JSONB)
    6. Update status to pending_review

    Args:
        case_id: Database Case ID

    Returns:
        Dict with generation result and action plan summary

    Raises:
        Handled gracefully with retry logic and status update
    """
    logger.info(f"Starting generate_action_plan_task for case_id={case_id}")

    try:
        result = asyncio.run(_generate_action_plan_async(case_id))
        return result
    except Exception as e:
        logger.error(f"Action plan generation failed for case_id={case_id}: {e}", exc_info=True)

        # Update case with error
        asyncio.run(_update_case_status_async(case_id, CaseStatus.FAILED, str(e)))

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


async def _generate_action_plan_async(case_id: Any) -> Dict[str, Any]:
    """Async implementation of action plan generation.

    Args:
        case_id: Database Case ID

    Returns:
        Generation result dictionary
    """
    async with AsyncSessionLocal() as session:
        # Fetch case and entities
        case = await session.get(Case, case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found in database")

        logger.info(f"Generating action plan for case: {case.case_number}")

        # Get all entities
        result = await session.execute(
            select(ExtractedEntity).where(ExtractedEntity.case_id == case_id)
        )
        entities = result.scalars().all()

        if not entities:
            logger.warning(f"No entities found for case {case_id}, using fallback")
            entities = []

        # Prepare entity data
        entity_data = [
            {
                "entity_type": e.entity_type,
                "extracted_text": e.extracted_text,
                "confidence_score": e.confidence_score,
                "bounding_box_coords": e.bounding_box_coords,
                "requires_review": e.requires_review,
            }
            for e in entities
        ]

        # Re-extract full document text from PDF for LLM context
        document_text = ""
        try:
            with PDFService(case.pdf_path) as pdf_service:
                pages = pdf_service.extract_all_pages()
                document_text = "\n".join(page.raw_text for page in pages)
        except Exception as e:
            logger.error(f"Failed to read PDF for LLM context: {e}")
            document_text = ""

        if not document_text.strip():
            document_text = f"Case: {case.case_number} (No text extracted from document)"

        # Generate action plan with full document text
        generator = ActionPlanGenerator(
            ollama_base_url=settings.ollama_base_url,
            model_name=settings.ollama_model,
            temperature=settings.llm_temperature,
            nvidia_nim_api_key=settings.nvidia_nim_api_key,
            nvidia_nim_model=settings.nvidia_nim_model,
            use_nvidia_nim=settings.use_nvidia_nim,
        )

        action_plan_dict = generator.generate_action_plan_with_fallback(
            case_number=case.case_number,
            case_summary=document_text,  # Pass full document text, not generic summary
            extracted_entities=entity_data,
        )

        # Update case with generated plan
        case.generated_action_plan = action_plan_dict
        await session.commit()

        logger.info(f"Action plan saved for case {case.case_number}")

        return {
            "case_id": case_id,
            "case_number": case.case_number,
            "status": "action_plan_generated",
            "directives_count": len(action_plan_dict.get("action_directives", [])),
        }
