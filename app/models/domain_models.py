"""Domain models for Nyaya Marga - Intelligent Ingestion Engine with HITL Verification.

Stages 3 & 4: Zero-Trust Verification + Compliance Dashboard
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
    Enum as SQLEnum,
    Date,
    Numeric,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, INET
from app.core.database import Base
import uuid


class UserRole(str, Enum):
    """User roles for RBAC (Role-Based Access Control)."""
    VIEWER = "viewer"
    OFFICER = "officer"
    ADMIN = "admin"


class CaseStatus(str, Enum):
    """Case processing status lifecycle (Stage 2 → 3 → 4)."""
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


class ExtractionStatus(str, Enum):
    """Individual extraction field verification status."""
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


class User(Base):
    """User model for authentication and role-based access."""
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=UserRole.VIEWER)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="actor", foreign_keys="AuditLog.actor_id")
    verified_extractions = relationship("Extraction", back_populates="verified_by_user", foreign_keys="Extraction.verified_by")
    assigned_cases = relationship("Case", back_populates="assigned_officer", foreign_keys="Case.assigned_officer_id")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class Case(Base):
    """Case document model - legal document for extraction, verification, and analysis."""
    __tablename__ = "cases"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number = Column(String(100), nullable=False, unique=True, index=True)
    court_name = Column(String(255), nullable=True)
    date_of_order = Column(Date, nullable=True)
    pdf_path = Column(String(512), nullable=False)

    # Processing status
    status = Column(SQLEnum(CaseStatus, values_callable=lambda obj: [e.value for e in obj]), default=CaseStatus.PROCESSING, nullable=False)

    # Verification workflow
    assigned_officer_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    nearest_deadline = Column(Date, nullable=True)
    submitted_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    verified_at = Column(DateTime, nullable=True)
    pipeline_completed_at = Column(DateTime, nullable=True)
    escalated = Column(Boolean, default=False)
    escalated_at = Column(DateTime, nullable=True)
    last_notified_at = Column(DateTime, nullable=True)

    # LLM-generated action plan (cached from teammate API)
    generated_action_plan = Column(JSON, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    extractions = relationship("Extraction", back_populates="case", cascade="all, delete-orphan")
    action_plan = relationship("ActionPlan", back_populates="case", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="case", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="case", cascade="all, delete-orphan")
    assigned_officer = relationship("User", back_populates="assigned_cases", foreign_keys=[assigned_officer_id])
    submitted_by_user = relationship("User", foreign_keys=[submitted_by])

    # For backward compatibility with existing ExtractedEntity
    entities = relationship("Extraction", back_populates="case", cascade="all, delete-orphan", overlaps="extractions")

    def __repr__(self) -> str:
        return f"<Case(id={self.id}, case_number={self.case_number}, status={self.status})>"


class Extraction(Base):
    """Extracted field with verification status - replaces ExtractedEntity."""
    __tablename__ = "extractions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(PG_UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    field_id = Column(PG_UUID(as_uuid=True), nullable=False)  # From teammate's API
    field_type = Column(String(50), nullable=False, index=True)  # BENCH, COURT, PETITIONER, etc.

    # Extracted values
    extracted_value = Column(Text, nullable=False)
    corrected_value = Column(Text, nullable=True)  # Set if officer edits
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0

    # Verification state
    status = Column(SQLEnum(ExtractionStatus, values_callable=lambda obj: [e.value for e in obj]), default=ExtractionStatus.PENDING, nullable=False)
    requires_review = Column(Boolean, nullable=False, default=False)
    manually_reviewed = Column(Boolean, default=False)

    # Verification user
    verified_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Constraint: low-confidence fields must be manually reviewed before approval
    __table_args__ = (
        CheckConstraint(
            "(confidence >= 0.75) OR (status IN ('edited', 'rejected')) OR (manually_reviewed = true)",
            name="ck_confidence_review_gate"
        ),
    )

    # Relationships
    case = relationship("Case", back_populates="extractions", foreign_keys=[case_id])
    spans = relationship("ExtractionSpan", back_populates="extraction", cascade="all, delete-orphan")
    verified_by_user = relationship("User", back_populates="verified_extractions", foreign_keys=[verified_by])

    def __repr__(self) -> str:
        return f"<Extraction(id={self.id}, case_id={self.case_id}, field_type={self.field_type}, status={self.status})>"


class ExtractionSpan(Base):
    """Bounding box coordinates for an extraction (from source PDF)."""
    __tablename__ = "extraction_spans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_id = Column(PG_UUID(as_uuid=True), ForeignKey("extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    span_id = Column(PG_UUID(as_uuid=True), nullable=False)  # From teammate's API
    page_num = Column(Integer, nullable=False)

    # PDF point coordinates (origin = bottom-left, 1 point = 1/72 inch)
    x0 = Column(Float, nullable=False)
    y0 = Column(Float, nullable=False)
    x1 = Column(Float, nullable=False)
    y1 = Column(Float, nullable=False)

    coordinate_space = Column(String(20), default="pdf_points", nullable=False)
    extraction_method = Column(String(10), nullable=False)  # DIGITAL or OCR

    # Relationships
    extraction = relationship("Extraction", back_populates="spans", foreign_keys=[extraction_id])

    def __repr__(self) -> str:
        return f"<ExtractionSpan(extraction={self.extraction_id}, page={self.page_num})>"


class ActionPlan(Base):
    """LLM-generated action plan (cached from teammate API)."""
    __tablename__ = "action_plans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(PG_UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Compliance analysis
    compliance_recommendation = Column(String(20), nullable=False)  # COMPLY, APPEAL, PARTIAL_COMPLY
    compliance_confidence = Column(Float, nullable=False)
    compliance_reasoning = Column(Text, nullable=False)

    # ROI analysis (in INR)
    compliance_cost_inr = Column(Numeric(15, 2), nullable=True)
    litigation_cost_inr = Column(Numeric(15, 2), nullable=True)
    cost_saving_inr = Column(Numeric(15, 2), nullable=True)
    roi_assumptions = Column(JSON, nullable=True)

    # Timeline and directives (store as JSONB)
    timeline_events = Column(JSON, default=list, nullable=False)
    directives = Column(JSON, default=list, nullable=False)

    # Raw LLM response for debugging
    raw_llm_response = Column(JSON, nullable=False)

    generated_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    case = relationship("Case", back_populates="action_plan", foreign_keys=[case_id])

    def __repr__(self) -> str:
        return f"<ActionPlan(case={self.case_id}, recommendation={self.compliance_recommendation})>"


class AuditLog(Base):
    """Immutable audit trail - INSERT only, no UPDATE/DELETE allowed."""
    __tablename__ = "audit_log"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(PG_UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    extraction_id = Column(PG_UUID(as_uuid=True), ForeignKey("extractions.id", ondelete="SET NULL"), nullable=True)

    action = Column(String(20), nullable=False, index=True)  # APPROVE, EDIT, REJECT, REOPEN, ESCALATE, ASSIGN
    actor_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    actor_role = Column(String(20), nullable=False)

    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)

    ip_address = Column(INET, nullable=True)
    session_id = Column(PG_UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    case = relationship("Case", back_populates="audit_logs", foreign_keys=[case_id])
    actor = relationship("User", back_populates="audit_logs", foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, actor={self.actor_id}, created_at={self.created_at})>"


class Notification(Base):
    """Notifications to prevent duplicate alerts."""
    __tablename__ = "notifications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(PG_UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    notification_type = Column(String(50), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    case = relationship("Case", back_populates="notifications", foreign_keys=[case_id])

    # UNIQUE constraint: prevent duplicate notifications on same day
    __table_args__ = (
        CheckConstraint(
            "DATE(sent_at) = CURRENT_DATE",  # Only today's date
            name="ck_notification_same_day"
        ),
    )

    def __repr__(self) -> str:
        return f"<Notification(case={self.case_id}, type={self.notification_type})>"


# Keep ExtractedEntity for backward compatibility (or remove if fully migrated)
class ExtractedEntity(Base):
    """Legacy: Use Extraction model instead."""
    __tablename__ = "extracted_entities"

    id = Column(Integer, primary_key=True)
    case_id = Column(PG_UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    extracted_text = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)
    bounding_box_coords = Column(JSON, nullable=True)
    requires_review = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    case = relationship("Case", foreign_keys=[case_id])

    def __repr__(self) -> str:
        return f"<ExtractedEntity(id={self.id}, case_id={self.case_id}, type={self.entity_type})>"
