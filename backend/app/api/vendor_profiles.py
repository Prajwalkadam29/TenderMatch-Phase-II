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
import uuid
from datetime import datetime, timezone
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

_FIELD_CONFIG = [
    # (path, label, section)
    ("identity.cin_llpin", "CIN/LLPIN Number", "Identity"),
    ("identity.udyam_registration_number", "Udyam Registration", "Identity"),
    ("identity.msme_category", "MSME Category", "Identity"),
    ("identity.nsic_registration_number", "NSIC Registration", "Identity"),
    ("identity.gem_seller_id", "GeM Seller ID", "Identity"),
    ("identity.dpiit_recognition_number", "DPIIT Recognition", "Identity"),
    
    ("geography.operational_districts", "Operational Districts", "Geography"),
    ("geography.willing_to_operate_in_new_states", "Growth Preference", "Geography"),
    ("geography.preferred_states", "Preferred States", "Geography"),
    
    ("business_domain.capability_description_freetext", "Capability Description", "Business"),
    ("business_domain.cpv_nic_codes", "CPV/NIC Codes", "Business"),
    ("business_domain.preferred_tender_categories", "Category Preferences", "Business"),
    ("business_domain.tender_value_range_preference", "Tender Value Preference", "Business"),
    
    ("financials.turnover_by_year", "Year-wise Turnover", "Financials"),
    ("financials.solvency_bank_name", "Solvency Bank Info", "Financials"),
    
    ("certifications.bis_nabl_accreditations", "Accreditations (BIS/NABL)", "Certifications"),
    ("certifications.mnre_empanelment", "MNRE Empanelment", "Certifications"),
    ("certifications.other_certifications", "Other Specialized Certs", "Certifications"),
    
    ("compliance.active_litigation", "Litigation Status", "Compliance"),
    ("compliance.gst_returns_compliant", "GST Compliance", "Compliance"),
    ("compliance.epf_esic_compliant", "EPF/ESIC Compliance", "Compliance"),
    
    ("notification_preferences.whatsapp_number", "WhatsApp Notifications", "Notifications"),
    ("notification_preferences.sms_number", "SMS Notifications", "Notifications"),
    ("notification_preferences.notification_frequency", "Alert Frequency", "Notifications"),
    ("notification_preferences.excluded_portals", "Portal Exclusions", "Notifications"),
    ("notification_preferences.min_days_to_deadline", "Deadline Buffer", "Notifications"),
]

def _compute_completeness(data: dict) -> tuple[float, list[dict]]:
    details = []
    filled_count = 0
    for path, label, section in _FIELD_CONFIG:
        parts = path.split(".")
        val = data
        is_filled = False
        try:
            for p in parts:
                val = val[p]
            if val is not None and val != "" and val != [] and val != {}:
                is_filled = True
                filled_count += 1
        except (KeyError, TypeError):
            pass
        
        details.append({
            "field_path": path,
            "label": label,
            "is_filled": is_filled,
            "section": section
        })
        
    pct = round((filled_count / len(_FIELD_CONFIG)) * 100, 1) if _FIELD_CONFIG else 0.0
    return pct, details


def _gen_vendor_id() -> str:
    return f"V-{uuid.uuid4().hex[:8].upper()}"


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
    completeness, details = _compute_completeness(data)

    # Sequence-based vendor_id
    vendor_id = f"V-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        **data,
        "vendor_id": vendor_id,
        "org_id": org_id,
        "user_id": user_id,
        "profile_version": 1,
        "profile_completeness_pct": completeness,
        "completeness_details": details,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
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
    completeness, details = _compute_completeness(data)

    update_data = {
        **data,
        "profile_version": doc.get("profile_version", 1) + 1,
        "profile_completeness_pct": completeness,
        "completeness_details": details,
        "updated_at": datetime.now(timezone.utc),
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
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )


# ── DUPLICATE ──────────────────────────────────────────────────────────────────

@router.post("/{profile_id}/duplicate", response_model=VendorProfileResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_vendor_profile(
    profile_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=400, detail="Invalid profile ID")

    doc = await db.vendor_profiles.find_one({"_id": ObjectId(profile_id), "is_active": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Vendor profile not found or inactive")
    
    if doc.get("user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    # Clone the document
    cloned_data = doc.copy()
    cloned_data.pop("_id")
    
    # Update fields for the new clone
    cloned_data["vendor_id"] = _gen_vendor_id()
    cloned_data["identity"]["company_legal_name"] = f"{doc['identity']['company_legal_name']} (Copy)"
    cloned_data["profile_version"] = 1
    cloned_data["created_at"] = datetime.now(timezone.utc)
    cloned_data["updated_at"] = datetime.now(timezone.utc)

    result = await db.vendor_profiles.insert_one(cloned_data)
    created = await db.vendor_profiles.find_one({"_id": result.inserted_id})
    return vendor_profile_helper(created)


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
