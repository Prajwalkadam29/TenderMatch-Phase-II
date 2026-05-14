import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from .config import settings


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against its bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a signed short-lived JWT access token.
    Embeds typ='access' to prevent refresh tokens being used as access tokens.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "typ": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create a signed long-lived JWT refresh token.
    Embeds typ='refresh' — cannot be used in place of an access token.
    Should be stored in an httpOnly, Secure, SameSite=Strict cookie.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "typ": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an access token.
    Raises JWTError if invalid or if token type is not 'access'.
    """
    payload = decode_token(token)
    if payload.get("typ") != "access":
        raise JWTError("Token type mismatch — expected access token")
    return payload


def decode_refresh_token(token: str) -> dict:
    """
    Decode and validate a refresh token.
    Raises JWTError if invalid or if token type is not 'refresh'.
    """
    payload = decode_token(token)
    if payload.get("typ") != "refresh":
        raise JWTError("Token type mismatch — expected refresh token")
    return payload

