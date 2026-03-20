from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from bson import ObjectId

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, MeResponse
from app.models.user import user_helper
from app.models.organization import org_helper

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    """Register a new user. If role=ADMIN1, also creates an organization."""
    db = get_db()

    # Check email uniqueness
    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Validate ADMIN1 registration
    if payload.role == "ADMIN1" and not payload.org_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Organization name is required when registering as Admin."
        )

    org_id = None

    # Create organization for ADMIN1
    if payload.role == "ADMIN1":
        org_doc = {
            "name": payload.org_name,
            "owner_id": None,  # Will update after user creation
            "industry": payload.org_industry,
            "description": None,
            "website": None,
            "location": None,
            "created_at": datetime.utcnow(),
            "is_active": True,
        }
        org_result = await db.organizations.insert_one(org_doc)
        org_id = str(org_result.inserted_id)

    # If USER with existing org_id provided
    if payload.role == "USER" and payload.org_id:
        org_id = payload.org_id

    # Create the user document
    user_doc = {
        "name": payload.name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "org_id": org_id,
        "preferences": {},
        "created_at": datetime.utcnow(),
        "is_active": True,
    }

    user_result = await db.users.insert_one(user_doc)
    user_id = str(user_result.inserted_id)

    # Update org's owner_id now that we have the user ID
    if payload.role == "ADMIN1" and org_id:
        await db.organizations.update_one(
            {"_id": ObjectId(org_id)},
            {"$set": {"owner_id": user_id}}
        )

    # Fetch full user doc to return
    created_user = await db.users.find_one({"_id": ObjectId(user_id)})
    user_data = user_helper(created_user)

    # Issue JWT
    token = create_access_token({"sub": user_id, "role": payload.role})

    return TokenResponse(access_token=token, user=user_data)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """Login with email and password, receive JWT token."""
    db = get_db()

    user = await db.users.find_one({"email": payload.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your admin."
        )

    user_data = user_helper(user)
    token = create_access_token({"sub": str(user["_id"]), "role": user["role"]})

    return TokenResponse(access_token=token, user=user_data)


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return MeResponse(
        id=str(current_user["_id"]),
        name=current_user.get("name", ""),
        email=current_user.get("email", ""),
        role=current_user.get("role", "USER"),
        org_id=current_user.get("org_id"),
        preferences=current_user.get("preferences", {}),
    )
