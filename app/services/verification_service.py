"""Verification workflow service for HITL approval/edit/reject."""
from datetime import datetime
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.domain_models import Extraction, Case, CaseStatus, ExtractionStatus, AuditLog
import uuid


async def check_verification_gate(extraction: Extraction) -> bool:
    """
    Check if a low-confidence extraction can be approved.
    Gate rule: confidence < 0.75 must have manual_reviewed = True.
    """
    if extraction.confidence < 0.75 and not extraction.manually_reviewed:
        return False
    return True


async def approve_extraction(
    case_id: str,
    field_id: str,
    current_user: dict,
    db: AsyncSession,
    ip_address: str = None
) -> dict:
    """Approve an extraction field."""
    # Find extraction
    result = await db.execute(
        select(Extraction).where(
            and_(
                Extraction.id == field_id,
                Extraction.case_id == case_id
            )
        )
    )
    extraction = result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    # Gate: low-confidence fields must be manually reviewed
    if extraction.confidence < 0.75 and not extraction.manually_reviewed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "MANUAL_REVIEW_REQUIRED",
                "message": f"Field confidence {extraction.confidence:.0%} is below 75% threshold. Officer must manually review this field.",
                "field_id": field_id,
                "confidence": extraction.confidence
            }
        )

    # Approve the extraction
    extraction.status = ExtractionStatus.APPROVED
    extraction.verified_by = uuid.UUID(current_user["user_id"])
    extraction.verified_at = datetime.utcnow()
    extraction.manually_reviewed = True

    # Audit log
    audit_entry = AuditLog(
        case_id=uuid.UUID(case_id),
        extraction_id=extraction.id,
        action="APPROVE",
        actor_id=uuid.UUID(current_user["user_id"]),
        actor_role=current_user["role"],
        ip_address=ip_address
    )
    db.add(audit_entry)
    await db.commit()

    return {"status": "approved", "field_id": str(extraction.id)}


async def edit_extraction(
    case_id: str,
    field_id: str,
    corrected_value: str,
    review_note: str,
    current_user: dict,
    db: AsyncSession,
    ip_address: str = None
) -> dict:
    """Edit an extraction field with officer correction."""
    # Find extraction
    result = await db.execute(
        select(Extraction).where(
            and_(
                Extraction.id == field_id,
                Extraction.case_id == case_id
            )
        )
    )
    extraction = result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    old_value = extraction.extracted_value
    extraction.corrected_value = corrected_value
    extraction.status = ExtractionStatus.EDITED
    extraction.verified_by = uuid.UUID(current_user["user_id"])
    extraction.verified_at = datetime.utcnow()
    extraction.manually_reviewed = True

    # Audit log
    audit_entry = AuditLog(
        case_id=uuid.UUID(case_id),
        extraction_id=extraction.id,
        action="EDIT",
        actor_id=uuid.UUID(current_user["user_id"]),
        actor_role=current_user["role"],
        old_value=old_value,
        new_value=corrected_value,
        reason=review_note,
        ip_address=ip_address
    )
    db.add(audit_entry)
    await db.commit()

    return {"status": "edited", "field_id": str(extraction.id), "corrected_value": corrected_value}


async def reject_extraction(
    case_id: str,
    field_id: str,
    reason: str,
    current_user: dict,
    db: AsyncSession,
    ip_address: str = None
) -> dict:
    """Reject an extraction field."""
    # Find extraction
    result = await db.execute(
        select(Extraction).where(
            and_(
                Extraction.id == field_id,
                Extraction.case_id == case_id
            )
        )
    )
    extraction = result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")

    extraction.status = ExtractionStatus.REJECTED
    extraction.rejection_reason = reason
    extraction.verified_by = uuid.UUID(current_user["user_id"])
    extraction.verified_at = datetime.utcnow()
    extraction.manually_reviewed = True

    # Audit log
    audit_entry = AuditLog(
        case_id=uuid.UUID(case_id),
        extraction_id=extraction.id,
        action="REJECT",
        actor_id=uuid.UUID(current_user["user_id"]),
        actor_role=current_user["role"],
        old_value=extraction.extracted_value,
        reason=reason,
        ip_address=ip_address
    )
    db.add(audit_entry)
    await db.commit()

    return {"status": "rejected", "field_id": str(extraction.id)}


async def verify_case_complete(
    case_id: str,
    current_user: dict,
    db: AsyncSession,
    ip_address: str = None
) -> dict:
    """
    Mark entire case as VERIFIED.
    Requirements:
    - All extractions must be APPROVED or EDITED
    - None can be PENDING or REJECTED
    """
    # Find case
    case_uuid = uuid.UUID(case_id)
    result = await db.execute(select(Case).where(Case.id == case_uuid))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check all extractions are actioned
    result = await db.execute(
        select(Extraction).where(
            and_(
                Extraction.case_id == case_uuid,
                Extraction.status.in_([ExtractionStatus.PENDING, ExtractionStatus.REJECTED])
            )
        )
    )
    unactioned = result.scalars().all()
    if unactioned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "UNACTIONED_FIELDS",
                "message": f"{len(unactioned)} extraction(s) not yet actioned",
                "count": len(unactioned)
            }
        )

    # Mark case as verified
    case.status = CaseStatus.VERIFIED
    case.verified_at = datetime.utcnow()

    # Audit log
    audit_entry = AuditLog(
        case_id=case_uuid,
        action="VERIFY",
        actor_id=uuid.UUID(current_user["user_id"]),
        actor_role=current_user["role"],
        reason="Case marked as fully verified",
        ip_address=ip_address
    )
    db.add(audit_entry)
    await db.commit()

    return {"status": "verified", "case_id": case_id}
