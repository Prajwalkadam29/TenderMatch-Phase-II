from pydantic import BaseModel, EmailStr
from typing import Optional, Literal


class RegisterRequest(BaseModel):
    """Request body for /auth/register."""
    name: str
    email: EmailStr
    password: str
    role: Literal["USER", "ADMIN1", "SUPERADMIN", "CUSTOMER_SUPPORT"] = "USER"
    # Required only when role == ADMIN1
    org_name: Optional[str] = None
    org_industry: Optional[str] = None
    # When registering a USER, admin can pass their org_id
    org_id: Optional[str] = None


class LoginRequest(BaseModel):
    """Request body for /auth/login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response returned after successful auth."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class MeResponse(BaseModel):
    """Response for GET /auth/me — mirrors what frontend User type expects."""
    id: str
    name: str
    email: str
    role: str
    org_id: Optional[str] = None
    preferences: dict = {}
