"""
pg_sync.py
----------
Dual-write service: mirrors MongoDB user/org writes into PostgreSQL.

Architecture (Phase 2 transition period):
- MongoDB remains the PRIMARY write target (existing code unchanged)
- This service writes to PostgreSQL AFTER a successful MongoDB write
- Read operations still use MongoDB (Phase 3 switches reads to PG)
- If the PostgreSQL write fails, it is logged but does NOT fail the request
  → This ensures Phase 2 is truly additive with zero regression risk

Error handling philosophy:
- PostgreSQL write failures are soft failures (warning log only)
- This is safe because MongoDB remains authoritative
- Phase 3 will flip this: PG becomes primary, MongoDB is the soft target
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.postgres import get_pg_session
from app.db.models.user import User
from app.db.models.organization import Organization
from app.db.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.db.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


# ── Organization sync ─────────────────────────────────────────────────────────

async def sync_org_to_pg(
    mongo_org_id: str,
    name: str,
    industry: Optional[str] = None,
    description: Optional[str] = None,
    website: Optional[str] = None,
    location: Optional[str] = None,
) -> Optional[uuid.UUID]:
    """
    Mirror a new organization from MongoDB into PostgreSQL.
    Returns the PostgreSQL UUID or None if the sync failed.
    """
    try:
        async with get_pg_session() as session:
            # Upsert: if mongo_id already exists (retry), update instead of insert
            existing = await session.scalar(
                select(Organization).where(Organization.mongo_id == mongo_org_id)
            )
            if existing:
                logger.debug("[PgSync] Organization %s already in PG (id=%s)", mongo_org_id, existing.id)
                return existing.id

            org = Organization(
                mongo_id=mongo_org_id,
                name=name,
                industry=industry,
                description=description,
                website=website,
                location=location,
                is_active=True,
            )
            session.add(org)
            await session.flush()  # Populates org.id before commit

            # Auto-create a free trial subscription for new orgs
            trial_end = datetime(
                datetime.now(timezone.utc).year,
                datetime.now(timezone.utc).month + 1,
                1,
                tzinfo=timezone.utc,
            ) if datetime.now(timezone.utc).month < 12 else datetime(
                datetime.now(timezone.utc).year + 1, 1, 1, tzinfo=timezone.utc
            )

            subscription = Subscription(
                org_id=org.id,
                plan=SubscriptionPlan.FREE,
                status=SubscriptionStatus.TRIALING,
                trial_ends_at=trial_end,
            )
            session.add(subscription)

            logger.info("[PgSync] Organization synced to PG: mongo_id=%s → pg_id=%s", mongo_org_id, org.id)
            return org.id

    except Exception as exc:
        logger.warning(
            "[PgSync] Failed to sync organization to PG (non-fatal): %s", exc,
            exc_info=True,
        )
        return None


# ── User sync ─────────────────────────────────────────────────────────────────

async def sync_user_to_pg(
    mongo_user_id: str,
    name: str,
    email: str,
    password_hash: str,
    role: str,
    mongo_org_id: Optional[str] = None,
    pg_org_id: Optional[uuid.UUID] = None,
) -> Optional[uuid.UUID]:
    """
    Mirror a new user from MongoDB into PostgreSQL.
    Returns the PostgreSQL UUID or None if the sync failed.

    pg_org_id: pass this if you already have the PG org UUID from sync_org_to_pg()
    mongo_org_id: used as a fallback to look up the org in PG
    """
    try:
        async with get_pg_session() as session:
            # Resolve org UUID
            resolved_org_id: Optional[uuid.UUID] = pg_org_id

            if resolved_org_id is None and mongo_org_id:
                org = await session.scalar(
                    select(Organization).where(Organization.mongo_id == mongo_org_id)
                )
                resolved_org_id = org.id if org else None

            # Upsert
            existing = await session.scalar(
                select(User).where(User.mongo_id == mongo_user_id)
            )
            if existing:
                logger.debug("[PgSync] User %s already in PG (id=%s)", mongo_user_id, existing.id)
                return existing.id

            user = User(
                mongo_id=mongo_user_id,
                name=name,
                email=email,
                password_hash=password_hash,
                role=role,
                org_id=resolved_org_id,
                is_active=True,
            )
            session.add(user)
            await session.flush()

            logger.info("[PgSync] User synced to PG: mongo_id=%s → pg_id=%s", mongo_user_id, user.id)
            return user.id

    except IntegrityError as exc:
        # Email uniqueness violation — user already exists with this email
        logger.warning("[PgSync] User email conflict for %s (non-fatal): %s", email, exc)
        return None
    except Exception as exc:
        logger.warning(
            "[PgSync] Failed to sync user to PG (non-fatal): %s", exc,
            exc_info=True,
        )
        return None


async def update_user_last_login(mongo_user_id: str) -> None:
    """Update last_login_at timestamp for a user after successful login."""
    try:
        async with get_pg_session() as session:
            await session.execute(
                update(User)
                .where(User.mongo_id == mongo_user_id)
                .values(last_login_at=datetime.now(timezone.utc))
            )
    except Exception as exc:
        logger.warning("[PgSync] Failed to update last_login_at (non-fatal): %s", exc)


# ── Audit log writer ──────────────────────────────────────────────────────────

async def write_audit_log(
    action: str,
    actor_mongo_id: Optional[str] = None,
    org_mongo_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict] = None,
    status: str = "success",
) -> None:
    """
    Write an immutable audit log entry to PostgreSQL.
    This is a best-effort write — failures are logged but never propagate.
    """
    try:
        async with get_pg_session() as session:
            # Resolve actor PG UUID from mongo_id
            actor_pg_id: Optional[uuid.UUID] = None
            if actor_mongo_id:
                user = await session.scalar(
                    select(User).where(User.mongo_id == actor_mongo_id)
                )
                actor_pg_id = user.id if user else None

            # Resolve org PG UUID from mongo_id
            org_pg_id: Optional[uuid.UUID] = None
            if org_mongo_id:
                org = await session.scalar(
                    select(Organization).where(Organization.mongo_id == org_mongo_id)
                )
                org_pg_id = org.id if org else None

            log_entry = AuditLog(
                actor_id=actor_pg_id,
                org_id=org_pg_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json=metadata,
                status=status,
            )
            session.add(log_entry)

    except Exception as exc:
        logger.warning("[PgSync] Failed to write audit log (non-fatal): %s", exc)
