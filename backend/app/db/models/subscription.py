"""
db/models/subscription.py
--------------------------
PostgreSQL ORM model for organization subscriptions.

Tracks which plan an organization is on, billing status, and feature limits.
This table enables SaaS monetisation (free/pro/enterprise tiers).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class SubscriptionPlan(str):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # One active subscription per org
        index=True,
    )

    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SubscriptionPlan.FREE,
        server_default="free",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SubscriptionStatus.TRIALING,
        server_default="trialing",
    )

    # Feature limits
    max_vendor_profiles: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    max_tenders_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    max_match_runs_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    ai_explanation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # Payment provider reference (Stripe/Razorpay)
    external_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    external_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Billing period
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Arbitrary metadata (e.g. custom feature flags)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

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

    # Relationship
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="subscription"
    )

    def __repr__(self) -> str:
        return f"<Subscription org_id={self.org_id} plan={self.plan} status={self.status}>"

    @property
    def is_active(self) -> bool:
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)
