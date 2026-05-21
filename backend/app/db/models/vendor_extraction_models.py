from typing import List, Optional
from pydantic import BaseModel

class YearlyTurnover(BaseModel):
    financial_year: Optional[str] = None
    turnover_inr: Optional[float] = None
    source_text: Optional[str] = None

class PastProject(BaseModel):
    project_title: Optional[str] = None
    client_name: Optional[str] = None
    client_type: Optional[str] = None
    contract_value_inr: Optional[float] = None
    year_of_completion: Optional[int] = None
    location_state: Optional[str] = None
    work_type: Optional[str] = None
    description: Optional[str] = None

class CertificationEntry(BaseModel):
    certification_name: Optional[str] = None
    issuing_body: Optional[str] = None
    valid_until: Optional[str] = None
    certificate_number: Optional[str] = None

class VendorExtractionResult(BaseModel):
    # Identity
    company_legal_name: Optional[str] = None
    registration_type: Optional[str] = None
    pan_number: Optional[str] = None
    gstin: Optional[str] = None
    year_of_incorporation: Optional[int] = None
    cin_number: Optional[str] = None

    # Geography
    registered_state: Optional[str] = None
    registered_city: Optional[str] = None
    operational_states: Optional[List[str]] = []

    # Business Domain
    primary_domains: Optional[List[str]] = []
    sub_domains: Optional[List[str]] = []
    cpv_nic_codes: Optional[List[str]] = []
    capabilities_freetext: Optional[str] = None

    # Financials
    average_annual_turnover_inr: Optional[float] = None
    net_worth_inr: Optional[float] = None
    turnover_by_year: Optional[List[YearlyTurnover]] = []
    solvency_certificate_available: Optional[bool] = None

    # Experience
    total_projects_completed: Optional[int] = None
    past_projects: Optional[List[PastProject]] = []
    years_in_business: Optional[int] = None

    # Certifications
    iso_certifications: Optional[List[CertificationEntry]] = []
    bis_nabl_accreditations: Optional[List[CertificationEntry]] = []
    domain_licenses: Optional[List[CertificationEntry]] = []

    # Compliance
    blacklisted: Optional[bool] = False
    msme_registered: Optional[bool] = None
    msme_category: Optional[str] = None

    # Extraction metadata
    extraction_confidence: Optional[float] = 0.0
    extraction_warnings: Optional[List[str]] = []
    source_pages_referenced: Optional[List[int]] = []
