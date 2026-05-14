"""
db/models/organization.py
--------------------------
PostgreSQL ORM model for organizations (tenants).

Every vendor profile, tender, and match result is scoped to an organization.
This is the root of the tenant isolation tree.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Cross-reference to MongoDB during dual-write period
    mongo_id: Mapped[Optional[str]] = mapped_column(String(24), nullable=True, unique=True, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # The user who created (owns) this org
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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

    # Relationships
    members: Mapped[List["User"]] = relationship(
        "User",
        back_populates="organization",
        foreign_keys="User.org_id",
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} name={self.name}>"
