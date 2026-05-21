"""
db/models/document.py
---------------------
SQLAlchemy ORM models for the PostgreSQL vector/relational layer.

Polyglot Persistence Architecture:
- Tender:        A THIN reference table. The parsed tender document (raw text,
                 LLM-extracted JSON, metadata) lives in MongoDB. This table only
                 stores the mongo_id bridge, the vector embedding for semantic
                 search, and a few indexed columns for fast filtering.
- VendorProfile: AUTHORITATIVE source of truth. Stored entirely in PostgreSQL
                 as JSONB. MongoDB is NOT used for vendor profiles.
"""

from sqlalchemy import (
    Column, String, JSON, ForeignKey, DateTime, Text,
    Integer, Boolean, Float, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
import uuid

from app.db.base import Base


class Tender(Base):
    """
    Thin pointer to a MongoDB tender document.

    Only the vector embedding and key filterable fields live here.
    Rich JSON (raw_text, structured_data, keywords) is fetched from MongoDB
    using mongo_id.
    """
    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── MongoDB bridge ──────────────────────────────────────────────────────
    mongo_id = Column(String(24), unique=True, index=True, nullable=False)

    # ── Tenant scope ────────────────────────────────────────────────────────
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), index=True)

    # ── Indexed fast-filter fields (duplicated from Mongo for query perf) ──
    filename = Column(String(255))
    scope = Column(Text)
    location = Column(String(255))

    # ── Semantic vector (all-MiniLM-L6-v2 = 384 dimensions) ────────────────
    embedding = Column(Vector(384))

    # ── Lightweight summary cache (certifications, keywords, etc.) ──────────
    summary = Column(JSONB)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VendorProfile(Base):
    """
    Authoritative vendor profile record — entirely in PostgreSQL.

    The complete profile (identity, geography, financials, certifications, etc.)
    is stored in the `profile_data` JSONB column. MongoDB is NOT used for
    vendor profiles — this is the single source of truth.
    """
    __tablename__ = "vendor_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Tenant + owner scope ────────────────────────────────────────────────
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identity shortcut columns (for fast filtering without JSONB lookup) ─
    vendor_id = Column(String(20), unique=True, index=True, nullable=False)
    business_name = Column(String(255), nullable=False, index=True)

    # ── Full profile stored as JSONB ────────────────────────────────────────
    # Contains: identity, geography, business_domain, financials,
    #           past_project_experience, certifications, compliance,
    #           notification_preferences
    profile_data = Column(JSONB, nullable=False)

    # ── Completeness tracking ───────────────────────────────────────────────
    profile_version = Column(Integer, nullable=False, default=1)
    profile_completeness_pct = Column(Float, nullable=False, default=0.0)
    completeness_details = Column(JSONB, nullable=True)

    # ── Status ──────────────────────────────────────────────────────────────
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    # ── Semantic vector of vendor capabilities ──────────────────────────────
    embedding = Column(Vector(384))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class VendorProfileWeight(Base):
    """
    Learned weights for the 7-dimension scoring engine.
    Follows a 3-tier fallback: Global -> Org -> Vendor.
    """
    __tablename__ = "vendor_profile_weights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ── Scope ─────────────────────────────────────────────────────────────────
    # If vendor_profile_id is null but org_id is present, it's an Org-level fallback weight
    vendor_profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendor_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        unique=True,
    )
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    # ── Learned Weights ───────────────────────────────────────────────────────
    weight_domain = Column(Float, nullable=False, default=0.25)
    weight_geography = Column(Float, nullable=False, default=0.15)
    weight_financial = Column(Float, nullable=False, default=0.20)
    weight_experience = Column(Float, nullable=False, default=0.15)
    weight_certification = Column(Float, nullable=False, default=0.10)
    weight_semantic = Column(Float, nullable=False, default=0.10)
    weight_confidence = Column(Float, nullable=False, default=0.05)
    
    # ── Tracking ──────────────────────────────────────────────────────────────
    total_feedback_count = Column(Integer, nullable=False, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

