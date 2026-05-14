"""
db/models/user.py
-----------------
PostgreSQL ORM model for users.

Relationship to MongoDB:
- This table is the AUTHORITATIVE source of truth for user identity.
- mongo_id stores the corresponding MongoDB ObjectId string for dual-write
  compatibility during the migration period.
- Once migration is complete, mongo_id can be dropped.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class UserRole(str):
    ADMIN1 = "ADMIN1"   # Organisation admin
    USER = "USER"       # Organisation member
    SUPER = "SUPER"     # Platform super-admin


class User(Base):
    """
    Relational user record.
    Stores identity, credentials, and org membership.
    JWT sub claim maps to str(id).
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Cross-reference to MongoDB during dual-write period
    mongo_id: Mapped[Optional[str]] = mapped_column(String(24), nullable=True, unique=True, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="USER",
        server_default="USER",
    )

    # FK to organizations (nullable for super-admins with no org)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="members", foreign_keys=[org_id]
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="actor", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
