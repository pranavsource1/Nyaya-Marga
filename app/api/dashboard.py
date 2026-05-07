from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.domain_models import AuditLog, Case, CaseStatus, ExtractedEntity, Extraction, User

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/cases")
async def get_dashboard_cases(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Case).order_by(Case.created_at.desc()))
    cases = result.scalars().all()

    rows = []
    for case in cases:
        legacy_count_result = await db.execute(
            select(func.count(ExtractedEntity.id)).where(ExtractedEntity.case_id == case.id)
        )
        extraction_count_result = await db.execute(
            select(func.count(Extraction.id)).where(Extraction.case_id == case.id)
        )
        entity_count = (legacy_count_result.scalar() or 0) + (extraction_count_result.scalar() or 0)

        assigned_officer = None
        if case.assigned_officer_id:
            officer = await db.get(User, case.assigned_officer_id)
            if officer:
                assigned_officer = {
                    "id": str(officer.id),
                    "email": officer.email,
                    "full_name": officer.full_name,
                    "department": officer.department,
                    "role": officer.role.value if hasattr(officer.role, "value") else officer.role,
                }

        rows.append(
            {
                "case_id": str(case.id),
                "case_number": case.case_number,
                "subject": case.court_name,
                "court_name": case.court_name,
                "department": assigned_officer["department"] if assigned_officer else None,
                "assigned_officer": assigned_officer,
                "status": case.status.value if hasattr(case.status, "value") else case.status,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "updated_at": case.updated_at.isoformat() if case.updated_at else None,
                "deadline": case.nearest_deadline.isoformat() if case.nearest_deadline else None,
                "error_message": case.error_message,
                "entity_count": entity_count,
            }
        )

    return rows


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    today = date.today()

    overdue_query = select(func.count(Case.id)).where(
        and_(
            Case.status == CaseStatus.VERIFIED,
            Case.nearest_deadline.isnot(None),
            Case.nearest_deadline <= today,
        )
    )

    critical_query = select(func.count(Case.id)).where(
        and_(
            Case.status == CaseStatus.VERIFIED,
            Case.nearest_deadline.isnot(None),
            Case.nearest_deadline > today,
            Case.nearest_deadline <= today + timedelta(days=7),
        )
    )

    first_of_month = datetime.combine(today.replace(day=1), datetime.min.time())
    verified_month_query = select(func.count(Case.id)).where(
        and_(
            Case.status == CaseStatus.VERIFIED,
            Case.verified_at.isnot(None),
            Case.verified_at >= first_of_month,
        )
    )

    pending_query = select(func.count(Case.id)).where(
        Case.status.in_(
            [
                CaseStatus.PENDING_REVIEW,
                CaseStatus.PENDING_VERIFICATION,
                CaseStatus.VERIFICATION_IN_PROGRESS,
            ]
        )
    )

    overdue_res = await db.execute(overdue_query)
    critical_res = await db.execute(critical_query)
    verified_res = await db.execute(verified_month_query)
    pending_res = await db.execute(pending_query)

    return {
        "verified_this_month": verified_res.scalar() or 0,
        "pending_verification": pending_res.scalar() or 0,
        "overdue_count": overdue_res.scalar() or 0,
        "critical_count": critical_res.scalar() or 0,
    }


@router.get("/audit")
async def get_audit_log(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditLog, Case.case_number, User.email, User.full_name)
        .join(Case, AuditLog.case_id == Case.id)
        .join(User, AuditLog.actor_id == User.id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )

    return [
        {
            "id": str(log.id),
            "case_id": str(log.case_id),
            "case_number": case_number,
            "extraction_id": str(log.extraction_id) if log.extraction_id else None,
            "action": log.action,
            "actor_id": str(log.actor_id),
            "actor_email": actor_email,
            "actor_name": actor_name,
            "actor_role": log.actor_role,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "reason": log.reason,
            "ip_address": str(log.ip_address) if log.ip_address else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log, case_number, actor_email, actor_name in result.all()
    ]


@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    return [
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }
        for user in users
    ]
