"""FastAPI route handlers for case ingestion and query.

Endpoints:
- POST /api/v1/cases/upload: Upload PDF and initiate processing
- GET /api/v1/cases/{case_id}/status: Query case status and entities
- GET /health: Health check

"""
import logging
import os
import uuid as uuid_mod
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, UploadFile, Depends, HTTPException, BackgroundTasks, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_db
from app.core.config import settings
from app.core.celery_app import celery_app
from app.models.domain_models import Case, CaseStatus, ExtractedEntity
from app.schemas.api_schemas import (
    CaseUploadRequest,
    CaseUploadResponse,
    CaseStatusResponse,
    EntityResponse,
    BoundingBoxResponse,
    HealthResponse,
)
from app.worker.tasks import process_case, generate_action_plan_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["cases"])


@router.post(
    "/cases/upload",
    response_model=CaseUploadResponse,
    status_code=202,
    summary="Upload case document for processing",
    description="Accepts a PDF file and metadata, stores it securely, and initiates async processing.",
)
async def upload_case(
    file: UploadFile,
    case_number: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> CaseUploadResponse:
    """Upload a PDF case document for intelligent ingestion.

    The PDF is securely stored, a Case record is created, and a Celery task
    is dispatched for async PDF extraction and NLP analysis.

    Args:
        file: PDF file upload
        case_number: Unique case identifier (e.g., "CASE-2024-001")
        db: Database session (injected)

    Returns:
        CaseUploadResponse with case_id and task_id for polling

    Raises:
        HTTPException: 400 if invalid file type or missing case_number
        HTTPException: 409 if case_number already exists
        HTTPException: 413 if file exceeds max size
        HTTPException: 500 if storage or database operation fails
    """
    # Validate inputs
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.content_type or not file.content_type.startswith("application/pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only PDF files accepted.",
        )

    if not case_number or not case_number.strip():
        raise HTTPException(status_code=400, detail="case_number is required")

    # Check case doesn't already exist
    existing = await db.execute(
        select(Case).where(Case.case_number == case_number)
    )
    if existing.scalar():
        raise HTTPException(
            status_code=409,
            detail=f"Case {case_number} already exists",
        )

    # Validate file size
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.max_upload_size_mb:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large: {file_size_mb:.1f}MB "
                f"(max: {settings.max_upload_size_mb}MB)"
            ),
        )

    # Save file securely
    try:
        # Use UUID to prevent collisions and directory traversal
        filename = f"{uuid_mod.uuid4()}_{case_number}.pdf"
        pdf_path = os.path.join(settings.upload_base_path, filename)

        with open(pdf_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved PDF for case {case_number}: {pdf_path}")

    except Exception as e:
        logger.error(f"Failed to save PDF for case {case_number}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to save PDF file"
        ) from e

    # Create Case record
    try:
        db_case = Case(
            case_number=case_number,
            pdf_path=pdf_path,
            status=CaseStatus.PROCESSING.value,
        )
        db.add(db_case)
        await db.commit()
        await db.refresh(db_case)

        logger.info(f"Created Case record: {db_case}")

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create Case record: {e}")
        # Clean up uploaded file
        try:
            os.remove(pdf_path)
        except:
            pass
        raise HTTPException(status_code=500, detail="Failed to create case record") from e

    # Dispatch Celery task
    try:
        task = process_case.delay(db_case.id, pdf_path)
        logger.info(f"Dispatched Celery task {task.id} for case {db_case.id}")

    except Exception as e:
        logger.error(f"Failed to dispatch Celery task: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to dispatch processing task"
        ) from e

    return CaseUploadResponse(
        case_id=db_case.id,
        task_id=task.id,
        case_number=case_number,
        status="processing",
    )


@router.get(
    "/cases/{case_id}/status",
    response_model=CaseStatusResponse,
    summary="Query case processing status",
    description="Returns current case status and extracted entities with coordinates.",
)
async def get_case_status(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> CaseStatusResponse:
    """Get the current status of a case and its extracted entities.

    Useful for polling to determine when processing is complete.

    Args:
        case_id: Database Case ID
        db: Database session (injected)

    Returns:
        CaseStatusResponse with status and entities

    Raises:
        HTTPException: 404 if case not found
    """
    try:
        # Fetch the case
        case = await db.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        # Fetch entities from extracted_entities table directly
        entity_result = await db.execute(
            select(ExtractedEntity)
            .where(ExtractedEntity.case_id == case_id)
            .order_by(ExtractedEntity.confidence_score.desc())
        )
        db_entities = entity_result.scalars().all()

        entity_count = len(db_entities)
        entities = [
            EntityResponse(
                id=e.id,
                entity_type=e.entity_type,
                extracted_text=e.extracted_text,
                confidence_score=e.confidence_score,
                bounding_box_coords=(
                    BoundingBoxResponse(**e.bounding_box_coords)
                    if e.bounding_box_coords
                    else None
                ),
                requires_review=e.requires_review,
                created_at=e.created_at,
            )
            for e in db_entities
        ]

        return CaseStatusResponse(
            case_id=case.id,
            case_number=case.case_number,
            status=case.status,
            created_at=case.created_at,
            updated_at=case.updated_at,
            error_message=case.error_message,
            entity_count=entity_count,
            entities=entities,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving case {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve case status") from e


@router.get(
    "/cases/{case_id}/action-plan",
    response_model=None,
    summary="Retrieve generated administrative action plan",
    description="Returns the AI-generated action plan for a case, suitable for Phase 4 frontend visualization.",
)
async def get_action_plan(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get the generated administrative action plan for a case.

    The action plan is generated via Phase 3 LLM processing and contains:
    - Compliance assessment
    - Litigation cost-benefit analysis
    - Statutory timeline analysis
    - Actionable departmental directives

    Args:
        case_id: Database Case ID
        db: Database session (injected)

    Returns:
        JSON object with action plan structure (or empty if not yet generated)

    Raises:
        HTTPException: 404 if case not found
        HTTPException: 202 if action plan not yet generated (pending generation)
    """
    try:
        case = await db.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        # Check if action plan has been generated
        if case.generated_action_plan is None:
            raise HTTPException(
                status_code=202,
                detail="Action plan not yet generated. Case may still be processing or scheduled for LLM generation.",
            )

        return case.generated_action_plan

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving action plan for case {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve action plan") from e


@router.post(
    "/cases/{case_id}/generate-action-plan",
    summary="Trigger action plan generation",
    description="Manually trigger action plan generation via LLM + RAG for a case. Useful for testing or manual retry.",
)
async def trigger_action_plan_generation(
    case_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Manually trigger action plan generation for a case.

    This endpoint dispatches a Celery task to generate a new action plan
    using the current entities and LLM/RAG pipeline.

    Useful for:
    - Testing the Phase 3 pipeline
    - Regenerating plans after entity verification
    - Manual retry after failures

    Args:
        case_id: Database Case ID
        db: Database session (injected)

    Returns:
        Dict with task_id for polling progress

    Raises:
        HTTPException: 404 if case not found
        HTTPException: 422 if case has no extracted entities
        HTTPException: 500 if task dispatch fails
    """
    try:
        # Check case exists
        case = await db.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        # Verify case has entities in extracted_entities table
        from sqlalchemy import func
        entity_count_result = await db.execute(
            select(func.count(ExtractedEntity.id))
            .where(ExtractedEntity.case_id == case_id)
        )
        entity_count = entity_count_result.scalar() or 0

        if entity_count == 0:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot generate action plan: Case {case_id} has no extracted entities. Complete Phase 1-2 processing first.",
            )

        # Dispatch Celery task
        try:
            task = generate_action_plan_task.delay(case_id)
            logger.info(f"Dispatched action plan generation task {task.id} for case {case_id}")

            return {
                "case_id": case_id,
                "task_id": task.id,
                "status": "generating",
                "message": "Action plan generation in progress. Poll /cases/{case_id}/action-plan to check result.",
            }

        except Exception as e:
            logger.error(f"Failed to dispatch action plan task: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to dispatch action plan generation task"
            ) from e

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering action plan for case {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to trigger action plan generation") from e


@router.get(
    "/cases",
    summary="List all cases",
    description="Returns all cases with basic info for the frontend dashboard.",
)
async def list_cases(
    db: AsyncSession = Depends(get_db),
):
    """List all cases."""
    result = await db.execute(select(Case).order_by(Case.created_at.desc()))
    cases = result.scalars().all()
    return [
        {
            "case_id": str(c.id),
            "case_number": c.case_number,
            "status": c.status.value if hasattr(c.status, 'value') else c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "error_message": c.error_message,
            "entity_count": 0,
        }
        for c in cases
    ]


@router.patch(
    "/cases/{case_id}/entities/{entity_id}",
    summary="Update an entity's status or value",
)
async def update_entity(
    case_id: str,
    entity_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Update an extracted entity (approve, reject, or edit)."""
    entity = await db.get(ExtractedEntity, entity_id)
    if not entity or str(entity.case_id) != case_id:
        raise HTTPException(status_code=404, detail="Entity not found")

    if "extracted_value" in data and data["extracted_value"]:
        entity.extracted_text = data["extracted_value"]
    if "status" in data:
        status_val = data["status"]
        if status_val == "VERIFIED":
            entity.requires_review = False
        elif status_val == "REJECTED":
            entity.requires_review = True

    await db.commit()
    await db.refresh(entity)

    return {
        "id": entity.id,
        "entity_type": entity.entity_type,
        "extracted_text": entity.extracted_text,
        "confidence_score": entity.confidence_score,
        "requires_review": entity.requires_review,
    }


@router.get(
    "/cases/{case_id}/pdf",
    summary="Serve PDF file for a case",
)
async def get_case_pdf(
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return the PDF file for a case."""
    from fastapi.responses import FileResponse

    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    pdf_path = case.pdf_path
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{case.case_number}.pdf",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["system"],
)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Health check endpoint for monitoring.

    Verifies database and Celery connectivity.

    Returns:
        HealthResponse with status details
    """
    try:
        # Test database connection
        await db.execute(select(1))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    try:
        # Test Celery connection
        celery_app.connection().connect()
        celery_status = "connected"
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        celery_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.api_version,
        database=db_status,
        celery=celery_status,
    )


@router.delete(
    "/cases/{case_id}",
    summary="Delete a case",
    description="Deletes a case and all associated data from the database.",
)
async def delete_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a case by its ID."""
    from sqlalchemy import delete
    from app.models.domain_models import ExtractedEntity

    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Manually delete extracted_entities to avoid ForeignKeyViolationError
    # since the legacy table's foreign key lacks ON DELETE CASCADE
    await db.execute(delete(ExtractedEntity).where(ExtractedEntity.case_id == case_id))
    
    # We must temporarily drop the immutability rule on audit_log so that the case cascade deletion succeeds
    from sqlalchemy import text
    await db.execute(text("DROP RULE IF EXISTS audit_log_no_delete ON audit_log"))
    
    # The new models have cascade="all, delete" for children.
    await db.delete(case)
    await db.commit()
    
    # Re-enable the immutability rule
    await db.execute(text("CREATE OR REPLACE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING"))
    await db.commit()
    
    # Optionally remove the PDF file
    if case.pdf_path and os.path.exists(case.pdf_path):
        try:
            os.remove(case.pdf_path)
        except Exception as e:
            logger.warning(f"Failed to delete PDF file for case {case_id}: {e}")

    return {"message": f"Case {case_id} deleted successfully"}
