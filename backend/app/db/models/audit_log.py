"""
db/models/audit_log.py
-----------------------
PostgreSQL ORM model for audit logs.

Records every significant state-changing action in the system.
Critical for:
- Security investigations (who changed what, when)
- Compliance reporting
- Debugging production issues

The actor_id is nullable so system-initiated actions (Celery tasks) can be recorded.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, JSON, Text, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Who performed the action (null = system/celery task)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Tenant scope
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # What happened
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        # Example values:
        # "user.register", "user.login", "user.logout"
        # "vendor_profile.create", "vendor_profile.update", "vendor_profile.delete"
        # "document.upload", "document.process"
        # "match.run", "match.view"
        # "subscription.upgrade", "subscription.cancel"
    )

    # What was affected
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Additional context (IP, user agent, changed fields, etc.)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Human-readable summary
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Network context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Outcome
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        server_default="success",
        # "success" | "failure" | "partial"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    # Relationship
    actor: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        # Composite index for common queries: "show all actions by org, ordered by time"
        Index("ix_audit_logs_org_created", "org_id", "created_at"),
        # Index for action-specific queries: "show all login failures"
        Index("ix_audit_logs_action_status", "action", "status"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action} actor={self.actor_id} at={self.created_at}>"
