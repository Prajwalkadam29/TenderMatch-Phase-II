// TenderMatch Vendor Profile — TypeScript Types (mirrors schema v1.0.0)

export interface GSTINEntry {
  gstin: string;
  state_code: string;
  state_name: string;
  is_primary: boolean;
}

export interface IdentityBlock {
  company_legal_name: string;
  registration_type: string;
  year_of_incorporation: number;
  pan_number: string;
  gstin_list: GSTINEntry[];
  cin_llpin?: string;
  udyam_registration_number?: string;
  msme_category?: string;
  nsic_registration_number?: string;
  gem_seller_id?: string;
  dpiit_recognition_number?: string;
}

export interface Address {
  street?: string;
  city?: string;
  district?: string;
  state?: string;
  state_code?: string;
  pincode?: string;
}

export interface GeographyBlock {
  registered_office_address?: Address;
  registered_states: string[];
  operational_states: string[];
  operational_districts?: string[];
  willing_to_operate_in_new_states?: boolean;
  preferred_states?: string[];
}

export interface TenderValueRange {
  min_inr?: number;
  max_inr?: number;
  currency: string;
}

export interface BusinessDomainBlock {
  primary_domains: string[];
  sub_domains: string[];
  capability_description_freetext?: string;
  cpv_nic_codes?: string[];
  preferred_tender_categories?: string[];
  tender_value_range_preference?: TenderValueRange;
}

export interface TurnoverByYear {
  financial_year: string;
  turnover_inr: number;
}

export interface FinancialsBlock {
  avg_annual_turnover_inr: number;
  turnover_by_year?: TurnoverByYear[];
  net_worth_status: string;
  solvency_certificate_available: boolean;
  solvency_bank_name?: string;
  esi_registration_number?: string;
  pf_registration_number?: string;
}

export interface PastProject {
  project_id?: string;
  project_title: string;
  work_type: string;
  work_description?: string;
  contract_value_inr: number;
  contract_value_excl_gst_inr?: number;
  client_name: string;
  client_type: string;
  location_state?: string;
  location_city?: string;
  year_of_completion: number;
  completion_certificate_available: boolean;
  tds_certificate_available: boolean;
  work_order_available: boolean;
  sub_contracted: boolean;
  remarks?: string;
}

export interface PastProjectExperienceBlock {
  projects: PastProject[];
  largest_single_project_value_inr?: number;
}

export interface ISOCertification {
  standard: string;
  category?: string;
  certifying_body?: string;
  valid_until?: string;
  certificate_number?: string;
}

export interface DomainLicense {
  license_type: string;
  license_number?: string;
  issuing_authority?: string;
  valid_until?: string;
  applicable_domain?: string;
}

export interface CertificationsBlock {
  iso_certifications: ISOCertification[];
  domain_licenses: DomainLicense[];
  bis_nabl_accreditations?: object[];
  mnre_empanelment?: boolean;
  other_certifications?: object[];
}

export interface ComplianceBlock {
  blacklisted_or_debarred: boolean;
  active_litigation?: boolean;
  gst_returns_compliant?: boolean;
  epf_esic_compliant?: boolean;
}

export interface NotificationPreferencesBlock {
  preferred_channels: string[];
  email: string;
  whatsapp_number?: string;
  sms_number?: string;
  minimum_match_score_threshold: number;
  notification_frequency?: string;
  excluded_portals?: string[];
  min_days_to_deadline?: number;
}

export interface VendorProfilePayload {
  identity: IdentityBlock;
  geography: GeographyBlock;
  business_domain: BusinessDomainBlock;
  financials: FinancialsBlock;
  past_project_experience: PastProjectExperienceBlock;
  certifications: CertificationsBlock;
  compliance: ComplianceBlock;
  notification_preferences: NotificationPreferencesBlock;
}

export interface VendorProfileResponse extends VendorProfilePayload {
  id: string;
  vendor_id?: string;
  org_id: string;
  user_id: string;
  profile_version: number;
  profile_completeness_pct: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Controlled vocabulary constants ──────────────────────────────────────────

export const REGISTRATION_TYPES = ['Pvt Ltd', 'LLP', 'Partnership', 'Sole Proprietorship', 'OPC', 'PSU', 'Trust', 'Society'];

export const MSME_CATEGORIES = ['Micro', 'Small', 'Medium'];

export const PRIMARY_DOMAINS = [
  'Civil & Construction', 'Electrical & Instrumentation', 'Mechanical',
  'IT & Software', 'Healthcare', 'Renewable Energy', 'Water & Sanitation',
  'Roads & Highways', 'Ports & Waterways', 'Railways', 'Telecom',
  'Supply / Procurement', 'Consultancy', 'O&M Services',
];

export const NET_WORTH_OPTIONS = ['Positive', 'Negative', 'Not Available'];

export const CLIENT_TYPES = ['Central Government', 'State Government', 'PSU', 'Municipal Body', 'Private', 'PPP'];

export const NOTIFICATION_CHANNELS = ['email', 'whatsapp', 'sms'];

export const NOTIFICATION_FREQUENCIES = ['realtime', 'daily_digest', 'weekly_digest'];

export const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
  'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
  'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
  'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry',
];

export const WORK_TYPES = [
  'Road and Highway Construction', 'Bridge and Culvert Works',
  'Civil Infrastructure Projects', 'Smart City Road Development',
  'Building Construction', 'Electrical Works', 'Water Supply & Sanitation',
  'IT Infrastructure', 'Healthcare Infrastructure', 'Railway Works',
  'Telecom Infrastructure', 'Supply & Procurement', 'Consulting Services',
  'O&M Services', 'Other',
];
