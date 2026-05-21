"""
Vendor Profile API Router
-------------------------
PostgreSQL-only implementation. Stores the complete vendor profile as JSONB.

POST   /vendor-profiles/           — create a new vendor profile
GET    /vendor-profiles/           — list all profiles owned by the current user
GET    /vendor-profiles/{id}       — get a single profile
PUT    /vendor-profiles/{id}       — full update
DELETE /vendor-profiles/{id}       — soft-delete
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.postgres import get_pg_db
from app.core.dependencies import get_current_user
from app.db.models.user import User
from app.db.models.document import VendorProfile
from app.models.vendor_profile import (
    VendorProfileCreate,
    VendorProfileResponse,
    IdentityBlock,
    GeographyBlock,
    BusinessDomainBlock,
)

router = APIRouter(prefix="/vendor-profiles", tags=["Vendor Profiles"])

# ── Completeness helper ────────────────────────────────────────────────────────

_FIELD_CONFIG = [
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

def _profile_to_response(profile: VendorProfile) -> dict:
    return {
        "id": str(profile.id),
        "vendor_id": profile.vendor_id,
        "org_id": str(profile.org_id),
        "user_id": str(profile.user_id),
        "profile_version": profile.profile_version,
        "profile_completeness_pct": profile.profile_completeness_pct,
        "completeness_details": profile.completeness_details,
        "is_active": profile.is_active,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        **profile.profile_data
    }

# ── CREATE ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=VendorProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor_profile(
    payload: VendorProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_pg_db),
):
    data = payload.model_dump(mode="json")
    completeness, details = _compute_completeness(data)
    vendor_id = _gen_vendor_id()

    profile = VendorProfile(
        org_id=current_user.org_id,
        user_id=current_user.id,
        vendor_id=vendor_id,
        business_name=payload.identity.company_legal_name,
        profile_data=data,
        profile_completeness_pct=completeness,
        completeness_details=details,
        is_active=True,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return _profile_to_response(profile)

# ── LIST ───────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[VendorProfileResponse])
async def list_vendor_profiles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_pg_db),
):
    result = await db.execute(
        select(VendorProfile).where(
            VendorProfile.user_id == current_user.id,
            VendorProfile.is_active == True
        )
    )
    profiles = result.scalars().all()
    return [_profile_to_response(p) for p in profiles]

# ── GET ONE ────────────────────────────────────────────────────────────────────

@router.get("/{profile_id}", response_model=VendorProfileResponse)
async def get_vendor_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_pg_db),
):
    try:
        pid = uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid profile ID format")

    profile = await db.scalar(select(VendorProfile).where(VendorProfile.id == pid))
    if not profile:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    if profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return _profile_to_response(profile)

# ── UPDATE ─────────────────────────────────────────────────────────────────────

@router.put("/{profile_id}", response_model=VendorProfileResponse)
async def update_vendor_profile(
    profile_id: str,
    payload: VendorProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_pg_db),
):
    try:
        pid = uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid profile ID format")

    profile = await db.scalar(select(VendorProfile).where(VendorProfile.id == pid))
    if not profile:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    if profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    data = payload.model_dump()
    completeness, details = _compute_completeness(data)

    profile.business_name = payload.identity.company_legal_name
    profile.profile_data = data
    profile.profile_completeness_pct = completeness
    profile.completeness_details = details
    profile.profile_version += 1
    profile.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(profile)
    return _profile_to_response(profile)

# ── DELETE ─────────────────────────────────────────────────────────────────────

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_pg_db),
):
    try:
        pid = uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid profile ID format")

    profile = await db.scalar(select(VendorProfile).where(VendorProfile.id == pid))
    if not profile:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    if profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    profile.is_active = False
    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()

# ── DUPLICATE ──────────────────────────────────────────────────────────────────

@router.post("/{profile_id}/duplicate", response_model=VendorProfileResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_vendor_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_pg_db),
):
    try:
        pid = uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid profile ID format")

    profile = await db.scalar(select(VendorProfile).where(VendorProfile.id == pid, VendorProfile.is_active == True))
    if not profile:
        raise HTTPException(status_code=404, detail="Vendor profile not found or inactive")
    if profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    new_data = profile.profile_data.copy()
    new_data["identity"]["company_legal_name"] = f"{new_data['identity']['company_legal_name']} (Copy)"

    new_profile = VendorProfile(
        org_id=current_user.org_id,
        user_id=current_user.id,
        vendor_id=_gen_vendor_id(),
        business_name=new_data["identity"]["company_legal_name"],
        profile_data=new_data,
        profile_completeness_pct=profile.profile_completeness_pct,
        completeness_details=profile.completeness_details,
        is_active=True,
    )
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    return _profile_to_response(new_profile)
