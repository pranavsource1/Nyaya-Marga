"""Verification endpoints for HITL workflow."""
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models.domain_models import (
    Extraction,
    ExtractionSpan,
    Case,
    ActionPlan,
    ExtractionStatus,
)
from app.services.verification_service import (
    approve_extraction,
    edit_extraction,
    reject_extraction,
    verify_case_complete,
)
import uuid

router = APIRouter(prefix="/api/v1/cases", tags=["verification"])


# Schemas

class ExtractionResponse(BaseModel):
    """Extraction field for verification."""
    id: str
    field_id: str
    field_type: str
    extracted_value: str
    corrected_value: Optional[str] = None
    confidence: float
    status: str
    requires_review: bool
    manually_reviewed: bool
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    rejection_reason: Optional[str] = None

    class Config:
        from_attributes = True


class ExtractionSpanResponse(BaseModel):
    """Bounding box for extraction highlighting."""
    id: str
    span_id: str
    page_num: int
    x0: float
    y0: float
    x1: float
    y1: float
    coordinate_space: str
    extraction_method: str

    class Config:
        from_attributes = True


class ExtractionsListResponse(BaseModel):
    """List of extractions for a case."""
    case_id: str
    extractions: list[ExtractionResponse]

    class Config:
        from_attributes = True


class EditExtractionRequest(BaseModel):
    """Edit extraction request."""
    corrected_value: str
    review_note: Optional[str] = None


class RejectExtractionRequest(BaseModel):
    """Reject extraction request."""
    reason: str


class VerifyCompleteResponse(BaseModel):
    """Response for verify-complete."""
    status: str
    case_id: str


# Endpoints

@router.get("/{case_id}/extractions", response_model=ExtractionsListResponse)
async def get_extractions(
    case_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all extractions for a case for verification."""
    case_uuid = uuid.UUID(case_id)

    # Check case exists
    result = await db.execute(select(Case).where(Case.id == case_uuid))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Case not found")

    # Fetch extractions
    result = await db.execute(
        select(Extraction).where(Extraction.case_id == case_uuid).order_by(Extraction.created_at)
    )
    extractions = result.scalars().all()

    extraction_responses = []
    for ext in extractions:
        extraction_responses.append(
            ExtractionResponse(
                id=str(ext.id),
                field_id=str(ext.field_id),
                field_type=ext.field_type,
                extracted_value=ext.extracted_value,
                corrected_value=ext.corrected_value,
                confidence=ext.confidence,
                status=ext.status.value if ext.status else ExtractionStatus.PENDING.value,
                requires_review=ext.requires_review,
                manually_reviewed=ext.manually_reviewed,
                verified_by=str(ext.verified_by) if ext.verified_by else None,
                verified_at=ext.verified_at.isoformat() if ext.verified_at else None,
                rejection_reason=ext.rejection_reason,
            )
        )

    return ExtractionsListResponse(
        case_id=case_id,
        extractions=extraction_responses
    )


@router.get("/{case_id}/extractions/{field_id}/spans", response_model=list[ExtractionSpanResponse])
async def get_extraction_spans(
    case_id: str,
    field_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get bounding boxes for an extraction field."""
    case_uuid = uuid.UUID(case_id)
    field_uuid = uuid.UUID(field_id)

    # Verify extraction exists and belongs to case
    result = await db.execute(
        select(Extraction).where(
            and_(
                Extraction.id == field_uuid,
                Extraction.case_id == case_uuid
            )
        )
    )
    extraction = result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    # Get spans
    result = await db.execute(
        select(ExtractionSpan).where(ExtractionSpan.extraction_id == field_uuid)
    )
    spans = result.scalars().all()

    return [
        ExtractionSpanResponse(
            id=str(span.id),
            span_id=str(span.span_id),
            page_num=span.page_num,
            x0=span.x0,
            y0=span.y0,
            x1=span.x1,
            y1=span.y1,
            coordinate_space=span.coordinate_space,
            extraction_method=span.extraction_method,
        )
        for span in spans
    ]


@router.post("/{case_id}/extractions/{field_id}/approve")
@router.post("/{case_id}/extractions/{field_id}/approve")
async def approve_field(
    case_id: str,
    field_id: str,
    current_user: dict = Depends(require_role("officer", "admin")),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Approve an extraction field."""
    ip_address = request.client.host if request else None
    return await approve_extraction(case_id, field_id, current_user, db, ip_address)


@router.post("/{case_id}/extractions/{field_id}/edit")
async def edit_field(
    case_id: str,
    field_id: str,
    body: EditExtractionRequest,
    current_user: dict = Depends(require_role("officer", "admin")),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Edit an extraction field with officer correction."""
    ip_address = request.client.host if request else None
    return await edit_extraction(
        case_id,
        field_id,
        body.corrected_value,
        body.review_note or "",
        current_user,
        db,
        ip_address
    )


@router.post("/{case_id}/extractions/{field_id}/reject")
async def reject_field(
    case_id: str,
    field_id: str,
    body: RejectExtractionRequest,
    current_user: dict = Depends(require_role("officer", "admin")),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Reject an extraction field."""
    ip_address = request.client.host if request else None
    return await reject_extraction(case_id, field_id, body.reason, current_user, db, ip_address)


@router.post("/{case_id}/verify-complete", response_model=VerifyCompleteResponse)
async def complete_verification(
    case_id: str,
    current_user: dict = Depends(require_role("officer", "admin")),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Mark entire case as VERIFIED (all fields must be actioned)."""
    ip_address = request.client.host if request else None
    return await verify_case_complete(case_id, current_user, db, ip_address)
