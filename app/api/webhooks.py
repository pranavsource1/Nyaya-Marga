from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.models.domain_models import CaseStatus
import uuid

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

@router.post("/case-complete")
async def receive_case_complete(payload: dict, db: AsyncSession = Depends(get_db)):
    case_id = payload.get("case_id")
    status = payload.get("status")

    if not case_id:
        return {"error": "Missing case_id"}

    if status and str(status).upper() == "FAILED":
        await db.execute(
            text("UPDATE cases SET status=:new_status WHERE id=:id"),
            {"id": uuid.UUID(case_id), "new_status": CaseStatus.NEEDS_REPROCESSING.value}
        )
        await db.commit()
        return {"received": True}
    
    return {"received": True, "cached_fields": 0}
