"""
auth.py
-------
Authentication endpoints:

POST /auth/register  → create account, receive access + refresh tokens
POST /auth/login     → authenticate, receive access + refresh tokens
POST /auth/refresh   → exchange valid refresh token for new access token
POST /auth/logout    → invalidate current access token via Redis blacklist
GET  /auth/me        → return current user profile
"""

from fastapi import APIRouter, HTTPException, status, Depends, Response, Cookie
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from jose import JWTError

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, MeResponse
from app.models.user import user_helper
from app.models.organization import org_helper
from app.services.pg_sync import sync_org_to_pg, sync_user_to_pg, update_user_last_login, write_audit_log

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ─── Cookie name constant ──────────────────────────────────────────────────────
REFRESH_COOKIE_NAME = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    """
    Store refresh token in an httpOnly, Secure, SameSite=Strict cookie.
    This prevents the token from being read by JavaScript (XSS protection).
    """
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=(settings.ENVIRONMENT != "development"),  # HTTPS only in production
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/auth/refresh",  # Cookie only sent to the refresh endpoint
    )


# ─── Register ──────────────────────────────────────────────────────────────────

from fastapi_limiter.depends import RateLimiter

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def register(payload: RegisterRequest, response: Response):
    """Register a new user. If role=ADMIN1, also creates an organization."""
    db = get_db()

    # Check email uniqueness
    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    # Validate ADMIN1 registration
    if payload.role == "ADMIN1" and not payload.org_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Organization name is required when registering as Admin.",
        )

    org_id = None

    # Create organization for ADMIN1
    if payload.role == "ADMIN1":
        org_doc = {
            "name": payload.org_name,
            "owner_id": None,
            "industry": payload.org_industry,
            "description": None,
            "website": None,
            "location": None,
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
        }
        org_result = await db.organizations.insert_one(org_doc)
        org_id = str(org_result.inserted_id)

    # If USER with existing org_id provided
    if payload.role == "USER" and payload.org_id:
        org_id = payload.org_id

    # Create the user document
    user_doc = {
        "name": payload.name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "org_id": org_id,
        "preferences": {},
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
    }

    user_result = await db.users.insert_one(user_doc)
    user_id = str(user_result.inserted_id)

    # Update org's owner_id
    if payload.role == "ADMIN1" and org_id:
        await db.organizations.update_one(
            {"_id": ObjectId(org_id)},
            {"$set": {"owner_id": user_id}},
        )

    # Fetch full user doc
    created_user = await db.users.find_one({"_id": ObjectId(user_id)})
    user_data = user_helper(created_user)

    # ── Phase 2: Dual-write to PostgreSQL (non-fatal) ─────────────────────────
    import asyncio
    pg_org_id = None
    if payload.role == "ADMIN1" and org_id:
        pg_org_id = await sync_org_to_pg(
            mongo_org_id=org_id,
            name=payload.org_name,
            industry=payload.org_industry,
        )
    await sync_user_to_pg(
        mongo_user_id=user_id,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        mongo_org_id=org_id,
        pg_org_id=pg_org_id,
    )
    await write_audit_log(
        action="user.register",
        actor_mongo_id=user_id,
        org_mongo_id=org_id,
        resource_type="user",
        resource_id=user_id,
        description=f"New {payload.role} registered: {payload.email}",
    )
    # ──────────────────────────────────────────────────────────────────────

    # Issue tokens
    token_payload = {"sub": user_id, "role": payload.role}
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token, user=user_data)


# ─── Login ─────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def login(payload: LoginRequest, response: Response):
    """Login with email and password. Returns access token + sets refresh cookie."""
    db = get_db()

    user = await db.users.find_one({"email": payload.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your admin.",
        )

    user_data = user_helper(user)
    token_payload = {"sub": str(user["_id"]), "role": user["role"]}
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    _set_refresh_cookie(response, refresh_token)

    # ── Phase 2: Dual-write to PostgreSQL (non-fatal) ─────────────────────────
    await update_user_last_login(mongo_user_id=str(user["_id"]))
    await write_audit_log(
        action="user.login",
        actor_mongo_id=str(user["_id"]),
        org_mongo_id=user.get("org_id"),
        resource_type="user",
        resource_id=str(user["_id"]),
        description=f"Login: {user['email']}",
    )
    # ──────────────────────────────────────────────────────────────────────

    return TokenResponse(access_token=access_token, user=user_data)


# ─── Refresh ───────────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a valid refresh token for a new access token",
    description=(
        "The refresh token must be present in the httpOnly 'refresh_token' cookie "
        "set during login or registration. Returns a new short-lived access token."
    ),
)
async def refresh_token_endpoint(
    response: Response,
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
        payload = decode_refresh_token(refresh_token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = get_db()
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise credentials_exception

    if not user:
        raise credentials_exception

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    # Issue new access token (and rotate refresh token)
    token_payload = {"sub": str(user["_id"]), "role": user["role"]}
    new_access_token = create_access_token(token_payload)
    new_refresh_token = create_refresh_token(token_payload)

    _set_refresh_cookie(response, new_refresh_token)

    user_data = user_helper(user)
    return TokenResponse(access_token=new_access_token, user=user_data)


# ─── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=MeResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return MeResponse(
        id=str(current_user["_id"]),
        name=current_user.get("name", ""),
        email=current_user.get("email", ""),
        role=current_user.get("role", "USER"),
        org_id=current_user.get("org_id"),
        preferences=current_user.get("preferences", {}),
    )


# ─── Logout ────────────────────────────────────────────────────────────────────

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.redis_client import get_redis

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    current_user: dict = Depends(get_current_user),
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
            # Blacklist for only the remaining TTL of the access token
            # (ACCESS_TOKEN_EXPIRE_MINUTES is short, so this is lightweight)
            expire_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            await redis.setex(f"blacklist:{token}", expire_seconds, "true")
        except Exception as exc:
            # Non-fatal — cookie will still be cleared
            import logging
            logging.getLogger(__name__).warning(
                "[Logout] Redis blacklist write failed (non-fatal): %s", exc
            )

    # Clear the refresh token cookie
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/auth/refresh",
    )

    return {"status": "ok", "message": "Successfully logged out"}
