from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime


class OrganizationInDB(BaseModel):
    """Represents an organization document as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    owner_id: str  # ObjectId string of the ADMIN1 user
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


def org_helper(org: dict) -> dict:
    """Convert a raw MongoDB organization document to a serializable dict."""
    return {
        "id": str(org["_id"]),
        "name": org.get("name", ""),
        "owner_id": org.get("owner_id", ""),
        "industry": org.get("industry"),
        "description": org.get("description"),
        "website": org.get("website"),
        "location": org.get("location"),
        "is_active": org.get("is_active", True),
        "created_at": org.get("created_at", "").isoformat() if org.get("created_at") else None,
    }
