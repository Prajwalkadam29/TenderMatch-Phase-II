from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime


class UserOut(BaseModel):
    """Public-facing user object (no password_hash)."""
    id: str
    name: str
    email: str
    role: str
    org_id: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


class UserCreate(BaseModel):
    """Request body for ADMIN1 creating a user inside their org."""
    name: str
    email: EmailStr
    password: str
    role: Literal["USER", "ADMIN1"] = "USER"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    preferences: Optional[dict] = None
    is_active: Optional[bool] = None
