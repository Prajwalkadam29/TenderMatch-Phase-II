"""
Vendor Profile API Router
-------------------------
POST   /vendor-profiles/           — create a new vendor profile (all 3 phases)
GET    /vendor-profiles/           — list all profiles owned by the current user
GET    /vendor-profiles/{id}       — get a single profile
PUT    /vendor-profiles/{id}       — full update (re-submit all phases)
DELETE /vendor-profiles/{id}       — soft-delete (is_active = False)
POST   /vendor-profiles/validate/phase/{phase} — validate a single phase payload
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional
from bson import ObjectId

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.vendor_profile import (
    VendorProfileCreate,
    VendorProfileResponse,
    VendorProfileInDB,
    vendor_profile_helper,
    # Phase blocks for partial validation
    IdentityBlock,
    GeographyBlock,
    BusinessDomainBlock,
    FinancialsBlock,
    PastProjectExperienceBlock,
    CertificationsBlock,
    ComplianceBlock,
    NotificationPreferencesBlock,
)

router = APIRouter(prefix="/vendor-profiles", tags=["Vendor Profiles"])


# ── Completeness helper ────────────────────────────────────────────────────────

_OPTIONAL_FIELDS = [
    # identity
    "identity.cin_llpin",
    "identity.udyam_registration_number",
    "identity.msme_category",
    "identity.nsic_registration_number",
    "identity.gem_seller_id",
    "identity.dpiit_recognition_number",
    # geography
    "geography.operational_districts",
    "geography.willing_to_operate_in_new_states",
    "geography.preferred_states",
    # business domain
    "business_domain.capability_description_freetext",
    "business_domain.cpv_nic_codes",
    "business_domain.preferred_tender_categories",
    "business_domain.tender_value_range_preference",
    # financials
    "financials.turnover_by_year",
    "financials.solvency_bank_name",
    # certifications
    "certifications.bis_nabl_accreditations",
    "certifications.mnre_empanelment",
    "certifications.other_certifications",
    # compliance
    "compliance.active_litigation",
    "compliance.gst_returns_compliant",
    "compliance.epf_esic_compliant",
    # notification
    "notification_preferences.whatsapp_number",
    "notification_preferences.sms_number",
    "notification_preferences.notification_frequency",
    "notification_preferences.excluded_portals",
    "notification_preferences.min_days_to_deadline",
]
_TOTAL = len(_OPTIONAL_FIELDS)


def _compute_completeness(data: dict) -> float:
    filled = 0
    for path in _OPTIONAL_FIELDS:
        parts = path.split(".")
        val = data
        try:
            for p in parts:
                val = val[p]
            if val is not None and val != "" and val != [] and val != {}:
                filled += 1
        except (KeyError, TypeError):
            pass
    return round((filled / _TOTAL) * 100, 1) if _TOTAL else 0.0


def _gen_vendor_id(seq: int) -> str:
    return f"V-{seq:05d}"


# ── CREATE ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=VendorProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor_profile(
    payload: VendorProfileCreate,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    user_id = str(current_user["_id"])
    org_id = current_user.get("org_id") or user_id

    data = payload.model_dump()
    completeness = _compute_completeness(data)

    # Sequence-based vendor_id
    count = await db.vendor_profiles.count_documents({})
    vendor_id = _gen_vendor_id(count + 1)

    doc = {
        **data,
        "vendor_id": vendor_id,
        "org_id": org_id,
        "user_id": user_id,
        "profile_version": 1,
        "profile_completeness_pct": completeness,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await db.vendor_profiles.insert_one(doc)
    created = await db.vendor_profiles.find_one({"_id": result.inserted_id})
    return vendor_profile_helper(created)


# ── LIST (current user) ────────────────────────────────────────────────────────

@router.get("/", response_model=List[VendorProfileResponse])
async def list_vendor_profiles(
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    user_id = str(current_user["_id"])
    cursor = db.vendor_profiles.find({"user_id": user_id, "is_active": True})
    profiles = []
    async for doc in cursor:
        profiles.append(vendor_profile_helper(doc))
    return profiles


# ── GET ONE ────────────────────────────────────────────────────────────────────

@router.get("/{profile_id}", response_model=VendorProfileResponse)
async def get_vendor_profile(
    profile_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=400, detail="Invalid profile ID")
    doc = await db.vendor_profiles.find_one({"_id": ObjectId(profile_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    if doc.get("user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    return vendor_profile_helper(doc)


# ── UPDATE ─────────────────────────────────────────────────────────────────────

@router.put("/{profile_id}", response_model=VendorProfileResponse)
async def update_vendor_profile(
    profile_id: str,
    payload: VendorProfileCreate,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=400, detail="Invalid profile ID")

    doc = await db.vendor_profiles.find_one({"_id": ObjectId(profile_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    if doc.get("user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    data = payload.model_dump()
    completeness = _compute_completeness(data)

    update_data = {
        **data,
        "profile_version": doc.get("profile_version", 1) + 1,
        "profile_completeness_pct": completeness,
        "updated_at": datetime.utcnow(),
    }

    await db.vendor_profiles.update_one(
        {"_id": ObjectId(profile_id)},
        {"$set": update_data}
    )
    updated = await db.vendor_profiles.find_one({"_id": ObjectId(profile_id)})
    return vendor_profile_helper(updated)


# ── SOFT DELETE ────────────────────────────────────────────────────────────────

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor_profile(
    profile_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=400, detail="Invalid profile ID")
    doc = await db.vendor_profiles.find_one({"_id": ObjectId(profile_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    if doc.get("user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    await db.vendor_profiles.update_one(
        {"_id": ObjectId(profile_id)},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )


# ── PHASE VALIDATION endpoints (used by frontend after each phase) ──────────────

class PhaseValidationResponse(BaseModel):
    valid: bool
    errors: Optional[List[str]] = []


@router.post("/validate/phase/1", response_model=PhaseValidationResponse)
async def validate_phase1(payload: IdentityBlock):
    return {"valid": True, "errors": []}


@router.post("/validate/phase/2", response_model=PhaseValidationResponse)
async def validate_phase2_geo(payload: GeographyBlock):
    return {"valid": True, "errors": []}


@router.post("/validate/phase/3", response_model=PhaseValidationResponse)
async def validate_phase3_domain(payload: BusinessDomainBlock):
    return {"valid": True, "errors": []}
