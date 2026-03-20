from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from bson import ObjectId
from datetime import datetime

from app.core.database import get_db
from app.core.security import hash_password
from app.core.dependencies import require_role
from app.schemas.user import UserOut, UserCreate
from app.models.user import user_helper

router = APIRouter(prefix="/organization", tags=["User Management"])


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_org_user(
    payload: UserCreate,
    current_user: dict = Depends(require_role("ADMIN1"))
):
    """ADMIN1 creates a new user in their organization."""
    db = get_db()
    admin_org_id = current_user.get("org_id")

    if not admin_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must have an organization before adding users."
        )

    # Check email uniqueness
    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    user_doc = {
        "name": payload.name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "role": payload.role,  # USER or ADMIN1
        "org_id": admin_org_id,
        "preferences": {},
        "created_at": datetime.utcnow(),
        "is_active": True,
    }

    result = await db.users.insert_one(user_doc)
    created = await db.users.find_one({"_id": result.inserted_id})
    return UserOut(**user_helper(created))


@router.get("/users", response_model=List[UserOut])
async def get_org_users(
    current_user: dict = Depends(require_role("ADMIN1"))
):
    """ADMIN1 lists all users in their organization."""
    db = get_db()
    admin_org_id = current_user.get("org_id")

    if not admin_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any organization."
        )

    cursor = db.users.find({"org_id": admin_org_id})
    users = []
    async for user in cursor:
        users.append(UserOut(**user_helper(user)))

    return users


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_user(
    user_id: str,
    current_user: dict = Depends(require_role("ADMIN1"))
):
    """ADMIN1 removes a user from their organization."""
    db = get_db()
    admin_org_id = current_user.get("org_id")

    # Validate ObjectId
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    # Find the target user
    target = await db.users.find_one({"_id": oid})
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    # Ensure the target user belongs to admin's org
    if target.get("org_id") != admin_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage users within your own organization."
        )

    # Prevent admin from deleting themselves
    if str(target["_id"]) == str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account."
        )

    await db.users.delete_one({"_id": oid})
    return None
