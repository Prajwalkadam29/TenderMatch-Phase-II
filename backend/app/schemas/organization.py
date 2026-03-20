from pydantic import BaseModel
from typing import Optional


class OrgCreate(BaseModel):
    """Request body for creating an organization."""
    name: str
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class OrgUpdate(BaseModel):
    """Request body for updating an organization profile."""
    name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


class OrgOut(BaseModel):
    """Public organization response."""
    id: str
    name: str
    owner_id: str
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
