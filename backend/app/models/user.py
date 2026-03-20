from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId
from datetime import datetime


class PyObjectId(str):
    """Custom type to handle MongoDB ObjectId serialization."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if ObjectId.is_valid(str(v)):
            return str(v)
        raise ValueError(f"Invalid ObjectId: {v}")


class UserInDB(BaseModel):
    """Represents a user document as stored in MongoDB."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    email: EmailStr
    password_hash: str
    role: str = "USER"  # USER | ADMIN1 | SUPERADMIN | CUSTOMER_SUPPORT
    org_id: Optional[str] = None
    preferences: dict = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


def user_helper(user: dict) -> dict:
    """Convert a raw MongoDB user document to a serializable dict."""
    return {
        "id": str(user["_id"]),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "USER"),
        "org_id": user.get("org_id"),
        "preferences": user.get("preferences", {}),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at", "").isoformat() if user.get("created_at") else None,
    }
