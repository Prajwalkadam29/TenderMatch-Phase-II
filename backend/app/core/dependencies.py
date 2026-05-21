from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .postgres import get_pg_db
from .security import decode_access_token
from app.db.models.user import User
from .redis_client import get_redis
from .config import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_pg_db),
):
    """
    Extract and validate the JWT bearer token against PostgreSQL.
    
    Security model:
    - Token type must be 'access'
    - Redis blacklist is checked if available
    - User is fetched from PostgreSQL using the UUID in the 'sub' claim
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials

    # 1. Validate token signature and type
    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError) as exc:
        logger.warning("[Auth] JWT validation failed: %s", exc)
        raise credentials_exception

    # 2. Check Redis blacklist
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
            raise
        except Exception as redis_exc:
            logger.warning("[Auth] Redis blacklist check failed: %s", redis_exc)

    # 3. Fetch user from PostgreSQL
    try:
        user = await db.scalar(select(User).where(User.id == user_id))
    except Exception as exc:
        logger.error("[Auth] Database lookup failed for user_id=%s: %s", user_id, exc)
        raise credentials_exception

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )

    return user

def require_role(*roles: str):
    """Dependency factory: enforces that the current user has one of the given roles."""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {list(roles)}"
            )
        return current_user
    return role_checker

require_super_admin = require_role("SUPER_ADMIN", "ADMIN1") # Allowing ADMIN1 for testing convenience
