"""
auth.py
-------
Authentication endpoints — PostgreSQL-only implementation.

All user and organization data is stored and fetched exclusively from
PostgreSQL (SQLAlchemy). MongoDB is NOT used for auth.

POST /auth/register  → create account, receive access + refresh tokens
POST /auth/login     → authenticate, receive access + refresh tokens
POST /auth/refresh   → exchange valid refresh token for new access token
POST /auth/logout    → invalidate current access token via Redis blacklist
GET  /auth/me        → return current user profile
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Response, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter.depends import RateLimiter
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.postgres import get_pg_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.core.config import settings
from app.core.redis_client import get_redis
from app.core.dependencies import get_current_user
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, MeResponse
from app.db.models.user import User
from app.db.models.organization import Organization
from app.db.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.db.models.audit_log import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE_NAME = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Store refresh token in an httpOnly, Secure, SameSite=Strict cookie."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=(settings.ENVIRONMENT != "development"),
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/auth/refresh",
    )


def _user_to_dict(user: User, org: Optional[Organization] = None) -> dict:
    """Serialize a SQLAlchemy User row into the dict the frontend expects."""
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "org_id": str(user.org_id) if user.org_id else None,
        "org_name": org.name if org else None,
        "preferences": {},
    }


async def _write_audit(
    session: AsyncSession,
    action: str,
    actor_id: Optional[uuid.UUID],
    org_id: Optional[uuid.UUID],
    resource_type: str,
    resource_id: str,
    description: str,
) -> None:
    """Best-effort audit log write — never raises."""
    try:
        entry = AuditLog(
            actor_id=actor_id,
            org_id=org_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            status="success",
        )
        session.add(entry)
        # Note: commit happens when the session context manager exits
    except Exception as exc:
        logger.warning("[Auth] Audit log write failed (non-fatal): %s", exc)


# ─── Register ──────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_pg_db),
):
    """Register a new user. If role=ADMIN1, also creates an organization."""

    # ── 1. Email uniqueness check ──────────────────────────────────────────
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    # ── 2. Validate ADMIN1 payload ─────────────────────────────────────────
    if payload.role == "ADMIN1" and not payload.org_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Organization name is required when registering as Admin.",
        )

    # ── 3. Create organization for ADMIN1 ──────────────────────────────────
    org: Optional[Organization] = None
    pg_org_id: Optional[uuid.UUID] = None

    if payload.role == "ADMIN1":
        org = Organization(
            name=payload.org_name,
            industry=payload.org_industry,
            is_active=True,
        )
        db.add(org)
        await db.flush()  # populate org.id before referencing it below

        # Auto-create a free-trial subscription
        now = datetime.now(timezone.utc)
        if now.month < 12:
            trial_end = now.replace(month=now.month + 1, day=1)
        else:
            trial_end = now.replace(year=now.year + 1, month=1, day=1)

        sub = Subscription(
            org_id=org.id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.TRIALING,
            trial_ends_at=trial_end,
        )
        db.add(sub)
        pg_org_id = org.id

    elif payload.role == "USER" and payload.org_id:
        # USER joining an existing org — verify the org exists
        try:
            pg_org_id = uuid.UUID(payload.org_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid org_id format.")
        org = await db.scalar(select(Organization).where(Organization.id == pg_org_id))
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found.")

    # ── 4. Create the user ────────────────────────────────────────────────
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        org_id=pg_org_id,
        is_active=True,
    )
    db.add(user)
    await db.flush()  # populate user.id

    # Set org owner for ADMIN1 (now that user.id is known)
    if payload.role == "ADMIN1" and org:
        org.owner_id = user.id

    # ── 5. Audit log ──────────────────────────────────────────────────────
    await _write_audit(
        session=db,
        action="user.register",
        actor_id=user.id,
        org_id=pg_org_id,
        resource_type="user",
        resource_id=str(user.id),
        description=f"New {payload.role} registered: {payload.email}",
    )

    # db session commits automatically when the context manager exits (get_pg_db)

    # ── 6. Issue tokens ───────────────────────────────────────────────────
    token_payload = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token, user=_user_to_dict(user, org))


# ─── Login ─────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_pg_db),
):
    """Login with email and password."""

    user = await db.scalar(select(User).where(User.email == payload.email))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your admin.",
        )

    # Update last_login_at
    user.last_login_at = datetime.now(timezone.utc)

    # Fetch org for response
    org: Optional[Organization] = None
    if user.org_id:
        org = await db.scalar(select(Organization).where(Organization.id == user.org_id))

    await _write_audit(
        session=db,
        action="user.login",
        actor_id=user.id,
        org_id=user.org_id,
        resource_type="user",
        resource_id=str(user.id),
        description=f"Login: {user.email}",
    )

    token_payload = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token, user=_user_to_dict(user, org))


# ─── Refresh ───────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a valid refresh token for a new access token",
)
async def refresh_token_endpoint(
    response: Response,
    db: AsyncSession = Depends(get_pg_db),
    refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    """Issue a new access token using the refresh token cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token — please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not refresh_token:
        raise credentials_exception

    try:
        token_payload = decode_refresh_token(refresh_token)
        user_id_str: str = token_payload.get("sub")
        if not user_id_str:
            raise credentials_exception
        user_uuid = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await db.scalar(select(User).where(User.id == user_uuid))
    if not user or not user.is_active:
        raise credentials_exception

    org: Optional[Organization] = None
    if user.org_id:
        org = await db.scalar(select(Organization).where(Organization.id == user.org_id))

    new_token_payload = {"sub": str(user.id), "role": user.role}
    new_access_token = create_access_token(new_token_payload)
    new_refresh_token = create_refresh_token(new_token_payload)
    _set_refresh_cookie(response, new_refresh_token)

    return TokenResponse(access_token=new_access_token, user=_user_to_dict(user, org))


# ─── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=MeResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return MeResponse(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        org_id=str(current_user.org_id) if current_user.org_id else None,
        preferences={},
    )



# ─── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    current_user: User = Depends(get_current_user),
):
    """
    Log out a user by:
    1. Blacklisting the current access token in Redis
    2. Clearing the refresh token cookie
    """
    token = credentials.credentials
    redis = get_redis()

    if redis:
        try:
            expire_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            await redis.setex(f"blacklist:{token}", expire_seconds, "true")
        except Exception as exc:
            logger.warning("[Logout] Redis blacklist write failed (non-fatal): %s", exc)

    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/auth/refresh")
    return {"status": "ok", "message": "Successfully logged out"}
