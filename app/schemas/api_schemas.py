"""Pydantic V2 schemas for strict API contracts.

These schemas ensure type safety and serialization for:
- Request/Response validation
- Phase 4 Next.js frontend integration
- Bounding box coordinate mapping for UI rendering
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID


class CaseStatusEnum(str, Enum):
    """Case status enumeration for API responses."""
    QUEUED = "queued"
    PROCESSING = "processing"
    PENDING_NLP = "pending_nlp"
    PENDING_REVIEW = "pending_review"
    PENDING_VERIFICATION = "pending_verification"
    VERIFICATION_IN_PROGRESS = "verification_in_progress"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_REPROCESSING = "needs_reprocessing"
    FAILED = "failed"
    CLOSED = "closed"


class BoundingBoxResponse(BaseModel):
    """Bounding box coordinates for entity location in document.

    Used by Phase 4 Next.js frontend to render entity highlights.
    """
    page: int = Field(..., description="Page number in PDF (0-indexed)")
    x0: float = Field(..., description="Top-left X coordinate")
    y0: float = Field(..., description="Top-left Y coordinate")
    x1: float = Field(..., description="Bottom-right X coordinate")
    y1: float = Field(..., description="Bottom-right Y coordinate")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 0,
                "x0": 100.5,
                "y0": 200.3,
                "x1": 250.7,
                "y1": 220.1
            }
        }


class EntityResponse(BaseModel):
    """Extracted entity with confidence and location data.

    Critical for Phase 4 frontend to map entities to visual highlights.
    """
    id: int
    entity_type: str = Field(..., description="Named entity type (PERSON, LOCATION, DATE, etc.)")
    extracted_text: str = Field(..., description="The actual text extracted")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence 0.0-1.0")
    bounding_box_coords: Optional[BoundingBoxResponse] = Field(
        None, description="Spatial coordinates for UI rendering"
    )
    requires_review: bool = Field(
        False, description="True if confidence < threshold, needs manual verification"
    )
    created_at: datetime

    class Config:
        from_attributes = True


class CaseUploadRequest(BaseModel):
    """Request model for case upload endpoint."""
    case_number: str = Field(..., min_length=1, max_length=255, description="Unique case identifier")


class CaseUploadResponse(BaseModel):
    """Response for case upload with async task tracking."""
    case_id: UUID = Field(..., description="Created case database ID")
    task_id: str = Field(..., description="Celery task ID for async processing")
    case_number: str
    status: CaseStatusEnum

    class Config:
        json_schema_extra = {
            "example": {
                "case_id": "123e4567-e89b-12d3-a456-426614174000",
                "task_id": "a9d11f90-6f8e-4cdd-a2a5-92cc02ad11f0",
                "case_number": "CASE-2024-001",
                "status": "processing"
            }
        }


class CaseStatusResponse(BaseModel):
    """Response model for case status query endpoint."""
    case_id: UUID
    case_number: str
    status: CaseStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None
    entity_count: int = Field(0, description="Number of extracted entities so far")
    entities: List[EntityResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "case_id": "123e4567-e89b-12d3-a456-426614174000",
                "case_number": "CASE-2024-001",
                "status": "pending_review",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:35:45Z",
                "error_message": None,
                "entity_count": 5,
                "entities": []
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    database: str = "connected"
    celery: str = "connected"
