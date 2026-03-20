from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from .database import get_db
from .security import decode_token
from bson import ObjectId

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """Extract and validate the JWT, return the user document from MongoDB."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = get_db()
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise credentials_exception

    if user is None:
        raise credentials_exception

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
