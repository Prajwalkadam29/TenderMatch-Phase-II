from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.schemas.organization import OrgCreate, OrgUpdate, OrgOut
from app.models.organization import org_helper

router = APIRouter(prefix="/organization", tags=["Organization"])


@router.post("/create", response_model=OrgOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrgCreate,
    current_user: dict = Depends(require_role("ADMIN1", "SUPERADMIN"))
):
    """Create an organization. Typically called automatically during ADMIN1 registration."""
    db = get_db()
    user_id = str(current_user["_id"])

    # Check if user already owns an org
    existing = await db.organizations.find_one({"owner_id": user_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an organization. Use PUT /organization/profile to update it."
        )

    from datetime import datetime
    org_doc = {
        "name": payload.name,
        "owner_id": user_id,
        "industry": payload.industry,
        "description": payload.description,
        "website": payload.website,
        "location": payload.location,
        "created_at": datetime.utcnow(),
        "is_active": True,
    }
    result = await db.organizations.insert_one(org_doc)
    org = await db.organizations.find_one({"_id": result.inserted_id})

    # Update user's org_id
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"org_id": str(result.inserted_id)}}
    )

    return OrgOut(**org_helper(org))


@router.get("/profile", response_model=OrgOut)
async def get_org_profile(current_user: dict = Depends(get_current_user)):
    """Get the organization profile of the current user."""
    db = get_db()
    org_id = current_user.get("org_id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not associated with any organization."
        )

    try:
        org = await db.organizations.find_one({"_id": ObjectId(org_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid organization ID.")

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found."
        )

    return OrgOut(**org_helper(org))


@router.put("/profile", response_model=OrgOut)
async def update_org_profile(
    payload: OrgUpdate,
    current_user: dict = Depends(require_role("ADMIN1", "SUPERADMIN"))
):
    """Update organization profile. Only ADMIN1 (owner) can do this."""
    db = get_db()
    org_id = current_user.get("org_id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not associated with any organization."
        )

    # Only update fields that were provided
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    await db.organizations.update_one(
        {"_id": ObjectId(org_id)},
        {"$set": update_data}
    )

    org = await db.organizations.find_one({"_id": ObjectId(org_id)})
    return OrgOut(**org_helper(org))
