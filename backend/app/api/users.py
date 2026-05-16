from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.postgres import get_pg_db
from app.core.security import hash_password
from app.core.dependencies import get_current_user, require_role
from app.schemas.user import UserOut, UserCreate, UserUpdate
from app.db.models.user import User

router = APIRouter(prefix="/organization", tags=["User Management"])

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_org_user(
    payload: UserCreate,
    current_user: User = Depends(require_role("ADMIN1")),
    db: AsyncSession = Depends(get_pg_db),
):
    """ADMIN1 creates a new user in their organization."""
    admin_org_id = current_user.org_id

    if not admin_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must have an organization before adding users."
        )

    # Check email uniqueness
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        org_id=admin_org_id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserOut(
        id=str(user.id),
        name=user.name,
        email=user.email,
        role=user.role,
        org_id=str(user.org_id) if user.org_id else None,
        created_at=user.created_at,
        is_active=user.is_active
    )

@router.get("/users", response_model=List[UserOut])
async def get_org_users(
    current_user: User = Depends(require_role("ADMIN1")),
    db: AsyncSession = Depends(get_pg_db),
):
    """ADMIN1 lists all users in their organization."""
    admin_org_id = current_user.org_id

    if not admin_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not associated with any organization."
        )

    result = await db.execute(select(User).where(User.org_id == admin_org_id))
    users = result.scalars().all()

    return [
        UserOut(
            id=str(u.id),
            name=u.name,
            email=u.email,
            role=u.role,
            org_id=str(u.org_id) if u.org_id else None,
            created_at=u.created_at,
            is_active=u.is_active
        ) for u in users
    ]

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_user(
    user_id: str,
    current_user: User = Depends(require_role("ADMIN1")),
    db: AsyncSession = Depends(get_pg_db),
):
    """ADMIN1 removes a user from their organization."""
    try:
        target_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    target = await db.scalar(select(User).where(User.id == target_id))
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    if target.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage users within your own organization."
        )

    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account."
        )

    await db.delete(target)
    await db.commit()
    return None

@router.put("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_pg_db),
):
    """Update current user's profile."""
    if payload.name is not None:
        current_user.name = payload.name
    
    # In Postgres model, preferences might be a JSON column or separate table.
    # Currently User model doesn't have a preferences column. 
    # I'll skip it or add it to the model later if needed.
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserOut(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        org_id=str(current_user.org_id) if current_user.org_id else None,
        created_at=current_user.created_at,
        is_active=current_user.is_active
    )
