"""
Vendor Profile — Pydantic/Motor model for MongoDB.
Mirrors the TenderMatch Vendor Profile Schema v1.0.0 exactly.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId


# ── Helpers ───────────────────────────────────────────────────────────────────

class PyObjectId(str):
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


# ── Identity sub-models ────────────────────────────────────────────────────────

class GSTINEntry(BaseModel):
    gstin: str
    state_code: str
    state_name: str
    is_primary: bool = False


class IdentityBlock(BaseModel):
    company_legal_name: str
    registration_type: str
    year_of_incorporation: int
    pan_number: str
    gstin_list: List[GSTINEntry]
    cin_llpin: Optional[str] = None
    udyam_registration_number: Optional[str] = None
    msme_category: Optional[str] = None
    nsic_registration_number: Optional[str] = None
    gem_seller_id: Optional[str] = None
    dpiit_recognition_number: Optional[str] = None


# ── Geography sub-models ───────────────────────────────────────────────────────

class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    pincode: Optional[str] = None


class GeographyBlock(BaseModel):
    registered_office_address: Optional[Address] = None
    registered_states: List[str]
    operational_states: List[str]
    operational_districts: Optional[List[str]] = []
    willing_to_operate_in_new_states: Optional[bool] = False
    preferred_states: Optional[List[str]] = []


# ── Business Domain sub-models ─────────────────────────────────────────────────

class TenderValueRange(BaseModel):
    min_inr: Optional[float] = None
    max_inr: Optional[float] = None
    currency: str = "INR"


class BusinessDomainBlock(BaseModel):
    primary_domains: List[str]
    sub_domains: List[str]
    capability_description_freetext: Optional[str] = None
    cpv_nic_codes: Optional[List[str]] = []
    preferred_tender_categories: Optional[List[str]] = []
    tender_value_range_preference: Optional[TenderValueRange] = None


# ── Financials sub-models ──────────────────────────────────────────────────────

class TurnoverByYear(BaseModel):
    financial_year: str
    turnover_inr: float


class FinancialsBlock(BaseModel):
    avg_annual_turnover_inr: float
    turnover_by_year: Optional[List[TurnoverByYear]] = []
    net_worth_status: str  # Positive | Negative | Not Available
    solvency_certificate_available: bool
    solvency_bank_name: Optional[str] = None
    esi_registration_number: Optional[str] = None
    pf_registration_number: Optional[str] = None


# ── Past Projects ──────────────────────────────────────────────────────────────

class PastProject(BaseModel):
    project_id: Optional[str] = None
    project_title: str
    work_type: str
    work_description: Optional[str] = None
    contract_value_inr: float
    contract_value_excl_gst_inr: Optional[float] = None
    client_name: str
    client_type: str  # Central Government | State Government | PSU | Municipal Body | Private | PPP
    location_state: Optional[str] = None
    location_city: Optional[str] = None
    year_of_completion: int
    completion_certificate_available: bool = False
    tds_certificate_available: bool = False
    work_order_available: bool = False
    sub_contracted: bool = False
    remarks: Optional[str] = None


class PastProjectExperienceBlock(BaseModel):
    projects: List[PastProject] = []
    largest_single_project_value_inr: Optional[float] = None


# ── Certifications ─────────────────────────────────────────────────────────────

class ISOCertification(BaseModel):
    standard: str
    category: Optional[str] = None
    certifying_body: Optional[str] = None
    valid_until: Optional[str] = None
    certificate_number: Optional[str] = None


class DomainLicense(BaseModel):
    license_type: str
    license_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    valid_until: Optional[str] = None
    applicable_domain: Optional[str] = None


class CertificationsBlock(BaseModel):
    iso_certifications: List[ISOCertification] = []
    domain_licenses: List[DomainLicense] = []
    bis_nabl_accreditations: Optional[List[dict]] = []
    mnre_empanelment: Optional[bool] = False
    other_certifications: Optional[List[dict]] = []


# ── Compliance ─────────────────────────────────────────────────────────────────

class ComplianceBlock(BaseModel):
    blacklisted_or_debarred: bool = False
    active_litigation: Optional[bool] = False
    gst_returns_compliant: Optional[bool] = True
    epf_esic_compliant: Optional[bool] = True


# ── Notification Preferences ───────────────────────────────────────────────────

class NotificationPreferencesBlock(BaseModel):
    preferred_channels: List[str] = ["email"]
    email: str
    whatsapp_number: Optional[str] = None
    sms_number: Optional[str] = None
    minimum_match_score_threshold: float = 0.65
    notification_frequency: Optional[str] = "realtime"
    excluded_portals: Optional[List[str]] = []
    min_days_to_deadline: Optional[int] = 7


# ── Top-level Vendor Profile document ─────────────────────────────────────────

class VendorProfileInDB(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    vendor_id: Optional[str] = None
    org_id: str                       # which organisation owns this profile
    user_id: str                      # which user created it
    profile_version: int = 1
    profile_completeness_pct: float = 0.0
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    identity: IdentityBlock
    geography: GeographyBlock
    business_domain: BusinessDomainBlock
    financials: FinancialsBlock
    past_project_experience: PastProjectExperienceBlock
    certifications: CertificationsBlock
    compliance: ComplianceBlock
    notification_preferences: NotificationPreferencesBlock

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


# ── Request/Response Pydantic models ───────────────────────────────────────────

class VendorProfileCreate(BaseModel):
    """Full create payload — all phases combined."""
    identity: IdentityBlock
    geography: GeographyBlock
    business_domain: BusinessDomainBlock
    financials: FinancialsBlock
    past_project_experience: PastProjectExperienceBlock
    certifications: CertificationsBlock
    compliance: ComplianceBlock
    notification_preferences: NotificationPreferencesBlock


class VendorProfileResponse(BaseModel):
    id: str
    vendor_id: Optional[str]
    org_id: str
    user_id: str
    profile_version: int
    profile_completeness_pct: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    identity: IdentityBlock
    geography: GeographyBlock
    business_domain: BusinessDomainBlock
    financials: FinancialsBlock
    past_project_experience: PastProjectExperienceBlock
    certifications: CertificationsBlock
    compliance: ComplianceBlock
    notification_preferences: NotificationPreferencesBlock


def vendor_profile_helper(doc: dict) -> dict:
    """Convert raw MongoDB document to serializable dict."""
    doc["id"] = str(doc.pop("_id"))
    return doc
