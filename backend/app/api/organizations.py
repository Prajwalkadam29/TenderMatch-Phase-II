from fastapi import APIRouter, HTTPException, status, Depends
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.postgres import get_pg_db
from app.core.dependencies import get_current_user, require_role
from app.schemas.organization import OrgCreate, OrgUpdate, OrgOut
from app.db.models.organization import Organization
from app.db.models.user import User

router = APIRouter(prefix="/organization", tags=["Organization"])

@router.post("/create", response_model=OrgOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrgCreate,
    current_user: User = Depends(require_role("ADMIN1", "SUPERADMIN")),
    db: AsyncSession = Depends(get_pg_db),
):
    """Create an organization."""
    # Check if user already owns an org
    existing = await db.scalar(select(Organization).where(Organization.owner_id == current_user.id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an organization. Use PUT /organization/profile to update it."
        )

    org = Organization(
        name=payload.name,
        owner_id=current_user.id,
        industry=payload.industry,
        description=payload.description,
        website=payload.website,
        location=payload.location,
        is_active=True,
    )
    db.add(org)
    await db.flush()  # populate org.id

    # Update user's org_id
    current_user.org_id = org.id
    await db.commit()
    await db.refresh(org)

    return OrgOut(
        id=str(org.id),
        name=org.name,
        industry=org.industry,
        description=org.description,
        website=org.website,
        location=org.location,
        owner_id=str(org.owner_id),
        created_at=org.created_at,
        is_active=org.is_active
    )

@router.get("/profile", response_model=OrgOut)
async def get_org_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_pg_db),
):
    """Get the organization profile of the current user."""
    org_id = current_user.org_id

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not associated with any organization."
        )

    org = await db.scalar(select(Organization).where(Organization.id == org_id))
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )

    return OrgOut(
        id=str(org.id),
        name=org.name,
        industry=org.industry,
        description=org.description,
        website=org.website,
        location=org.location,
        owner_id=str(org.owner_id),
        created_at=org.created_at,
        is_active=org.is_active
    )

@router.put("/profile", response_model=OrgOut)
async def update_org_profile(
    payload: OrgUpdate,
    current_user: User = Depends(require_role("ADMIN1", "SUPERADMIN")),
    db: AsyncSession = Depends(get_pg_db),
):
    """Update organization profile. Only ADMIN1 (owner) can do this."""
    org_id = current_user.org_id

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not associated with any organization."
        )

    org = await db.scalar(select(Organization).where(Organization.id == org_id))
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )

    if payload.name is not None:
        org.name = payload.name
    if payload.industry is not None:
        org.industry = payload.industry
    if payload.description is not None:
        org.description = payload.description
    if payload.website is not None:
        org.website = payload.website
    if payload.location is not None:
        org.location = payload.location

    await db.commit()
    await db.refresh(org)

    return OrgOut(
        id=str(org.id),
        name=org.name,
        industry=org.industry,
        description=org.description,
        website=org.website,
        location=org.location,
        owner_id=str(org.owner_id),
        created_at=org.created_at,
        is_active=org.is_active
    )
