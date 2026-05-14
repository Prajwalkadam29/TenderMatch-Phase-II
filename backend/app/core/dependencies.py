from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
import logging

from .database import get_db
from .security import decode_access_token
from bson import ObjectId

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer()


from .redis_client import get_redis


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """
    Extract and validate the JWT bearer token.
    
    Security model:
    - Token type must be 'access' (prevents refresh token reuse as bearer)
    - Redis blacklist is checked when Redis is available (best-effort)
    - With short-lived tokens (15 min), the blacklist window is small
    - Falls back gracefully if Redis is unavailable — logs a warning
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials

    # ── 1. Validate token signature and type ─────────────────────────────────
    try:
        payload = decode_access_token(token)  # raises JWTError if wrong type
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as exc:
        logger.warning("[Auth] JWT validation failed: %s", exc)
        raise credentials_exception

    # ── 2. Check Redis blacklist (best-effort; logged if unavailable) ─────────
    redis = get_redis()
    if redis is not None:
        try:
            is_blacklisted = await redis.get(f"blacklist:{token}")
            if is_blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked — please log in again",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise  # re-raise blacklist 401 as-is
        except Exception as redis_exc:
            # Redis unavailable: log and continue — access tokens are short-lived
            logger.warning(
                "[Auth] Redis blacklist check failed (Redis unavailable): %s. "
                "Proceeding with JWT validation only.", redis_exc
            )
    else:
        logger.warning("[Auth] Redis client not available — blacklist check skipped")

    # ── 3. Fetch user from database ───────────────────────────────────────────
    db = get_db()
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception as exc:
        logger.error("[Auth] Database lookup failed for user_id=%s: %s", user_id, exc)
        raise credentials_exception

    if user is None:
        raise credentials_exception

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )

    return user


def require_role(*roles: str):
    """Dependency factory: enforces that the current user has one of the given roles."""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {list(roles)}"
            )
        return current_user
    return role_checker

