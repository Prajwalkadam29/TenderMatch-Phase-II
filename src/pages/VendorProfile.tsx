import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Phase1Identity } from '../components/vendorProfile/Phase1Identity';
import { Phase1Geography } from '../components/vendorProfile/Phase1Geography';
import { Phase2BusinessDomain, Phase2Financials } from '../components/vendorProfile/Phase2Business';
import { Phase2Projects } from '../components/vendorProfile/Phase2Projects';
import { Phase3Certifications, Phase3Compliance, Phase3Notifications } from '../components/vendorProfile/Phase3';
import { vendorProfileService } from '../services/vendorProfileApi';
import type {
  VendorProfilePayload,
  IdentityBlock,
  GeographyBlock,
  BusinessDomainBlock,
  FinancialsBlock,
  PastProjectExperienceBlock,
  CertificationsBlock,
  ComplianceBlock,
  NotificationPreferencesBlock,
  VendorProfileResponse,
} from '../types/vendorProfile';
import '../components/vendorProfile/VendorProfileForm.css';

/* ── Default empty state ─────────────────────────────────────────────────── */
const defaultIdentity: IdentityBlock = {
  company_legal_name: '',
  registration_type: '',
  year_of_incorporation: 0,
  pan_number: '',
  gstin_list: [],
};

const defaultGeography: GeographyBlock = {
  registered_office_address: {},
  registered_states: [],
  operational_states: [],
  operational_districts: [],
  willing_to_operate_in_new_states: false,
  preferred_states: [],
};

const defaultBusiness: BusinessDomainBlock = {
  primary_domains: [],
  sub_domains: [],
  capability_description_freetext: '',
  cpv_nic_codes: [],
  preferred_tender_categories: [],
  tender_value_range_preference: undefined,
};

const defaultFinancials: FinancialsBlock = {
  avg_annual_turnover_inr: 0,
  turnover_by_year: [],
  net_worth_status: '',
  solvency_certificate_available: false,
  solvency_bank_name: '',
  esi_registration_number: '',
  pf_registration_number: '',
};

const defaultProjects: PastProjectExperienceBlock = { projects: [] };

const defaultCerts: CertificationsBlock = {
  iso_certifications: [],
  domain_licenses: [],
  bis_nabl_accreditations: [],
  mnre_empanelment: false,
  other_certifications: [],
};

const defaultCompliance: ComplianceBlock = {
  blacklisted_or_debarred: false,
  active_litigation: false,
  gst_returns_compliant: true,
  epf_esic_compliant: true,
};

const defaultNotifications: NotificationPreferencesBlock = {
  preferred_channels: ['email'],
  email: '',
  minimum_match_score_threshold: 0.65,
  notification_frequency: 'realtime',
  min_days_to_deadline: 7,
};

/* ── Phase Config ─────────────────────────────────────────────────────────── */
const PHASES = [
  {
    id: 1,
    label: 'Phase 1',
    title: 'Company Identity & Geography',
    subPhases: ['Identity', 'Geography'],
  },
  {
    id: 2,
    label: 'Phase 2',
    title: 'Business & Financials',
    subPhases: ['Business Domain', 'Financials', 'Past Projects'],
  },
  {
    id: 3,
    label: 'Phase 3',
    title: 'Certifications & Preferences',
    subPhases: ['Certifications', 'Compliance', 'Notifications'],
  },
];

/* ── Validation — one function per sub-phase ──────────────────────────────── */
function validateIdentity(identity: IdentityBlock): string[] {
  const errs: string[] = [];
  if (!identity.company_legal_name.trim()) errs.push('Company legal name is required');
  if (!identity.registration_type) errs.push('Registration type is required');
  if (!identity.year_of_incorporation || identity.year_of_incorporation < 1900)
    errs.push('Valid year of incorporation is required');
  if (!identity.pan_number.trim() || !/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(identity.pan_number))
    errs.push('Valid PAN number is required (format: AAAAA9999A)');
  if (identity.gstin_list.length === 0) errs.push('At least one GSTIN is required');
  return errs;
}

function validateGeography(geo: GeographyBlock): string[] {
  const errs: string[] = [];
  if (!geo.registered_office_address?.city?.trim()) errs.push('Registered office city is required');
  if (!geo.registered_office_address?.state?.trim()) errs.push('Registered office state is required');
  if (geo.registered_states.length === 0) errs.push('At least one registered state is required');
  if (geo.operational_states.length === 0) errs.push('At least one operational state is required');
  return errs;
}

function validateBusinessDomain(biz: BusinessDomainBlock): string[] {
  const errs: string[] = [];
  if (biz.primary_domains.length === 0) errs.push('At least one primary domain is required');
  if (biz.sub_domains.length === 0)
    errs.push('At least one sub-domain/specialization is required — type and click "+ Add" or press Enter');
  return errs;
}

function validateFinancials(fin: FinancialsBlock): string[] {
  const errs: string[] = [];
  if (!fin.avg_annual_turnover_inr || fin.avg_annual_turnover_inr <= 0)
    errs.push('Average annual turnover is required');
  if (!fin.net_worth_status) errs.push('Net worth status is required');
  return errs;
}

function validateProjects(proj: PastProjectExperienceBlock): string[] {
  const errs: string[] = [];
  if (proj.projects.length === 0) errs.push('At least one past project is required');
  return errs;
}

function validateNotifications(notif: NotificationPreferencesBlock, comp: ComplianceBlock): string[] {
  const errs: string[] = [];
  if (notif.preferred_channels.length === 0) errs.push('At least one notification channel is required');
  if (!notif.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(notif.email))
    errs.push('Valid email address is required');
  if (comp.blacklisted_or_debarred)
    errs.push('⚠️ Blacklisted/debarred vendors cannot be registered');
  return errs;
}

/* ── Main Page Component ─────────────────────────────────────────────────── */
export const VendorProfilePage: React.FC = () => {
  const navigate = useNavigate();

  const [phase, setPhase] = useState(1);
  const [subPhase, setSubPhase] = useState(0);

  const [identity, setIdentity] = useState<IdentityBlock>(defaultIdentity);
  const [geography, setGeography] = useState<GeographyBlock>(defaultGeography);
  const [business, setBusiness] = useState<BusinessDomainBlock>(defaultBusiness);
  const [financials, setFinancials] = useState<FinancialsBlock>(defaultFinancials);
  const [projects, setProjects] = useState<PastProjectExperienceBlock>(defaultProjects);
  const [certifications, setCertifications] = useState<CertificationsBlock>(defaultCerts);
  const [compliance, setCompliance] = useState<ComplianceBlock>(defaultCompliance);
  const [notifications, setNotifications] = useState<NotificationPreferencesBlock>(defaultNotifications);

  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [saved, setSaved] = useState<VendorProfileResponse | null>(null);

  const currentPhaseConfig = PHASES[phase - 1];
  const totalSubPhases = currentPhaseConfig.subPhases.length;

  /* ── Render sub-phase component ─────────────────────────────────────────── */
  const renderSubPhase = () => {
    if (phase === 1) {
      if (subPhase === 0) return <Phase1Identity data={identity} onChange={setIdentity} />;
      if (subPhase === 1) return <Phase1Geography data={geography} onChange={setGeography} />;
    }
    if (phase === 2) {
      if (subPhase === 0) return <Phase2BusinessDomain data={business} onChange={setBusiness} />;
      if (subPhase === 1) return <Phase2Financials data={financials} onChange={setFinancials} />;
      if (subPhase === 2) return <Phase2Projects data={projects} onChange={setProjects} />;
    }
    if (phase === 3) {
      if (subPhase === 0) return <Phase3Certifications data={certifications} onChange={setCertifications} />;
      if (subPhase === 1) return <Phase3Compliance data={compliance} onChange={setCompliance} />;
      if (subPhase === 2) return <Phase3Notifications data={notifications} onChange={setNotifications} />;
    }
    return null;
  };

  /* ── Navigation ─────────────────────────────────────────────────────────── */
  const validateCurrentPhase = (): string[] => {
    // Phase 1
    if (phase === 1 && subPhase === 0) return validateIdentity(identity);
    if (phase === 1 && subPhase === 1) return validateGeography(geography);
    // Phase 2 — validate each sub-tab individually
    if (phase === 2 && subPhase === 0) return validateBusinessDomain(business);
    if (phase === 2 && subPhase === 1) return validateFinancials(financials);
    if (phase === 2 && subPhase === 2) return validateProjects(projects);
    // Phase 3
    if (phase === 3 && subPhase === 2) return validateNotifications(notifications, compliance);
    return [];
  };

  const handleNext = async () => {
    const errs = validateCurrentPhase();
    if (errs.length > 0) { setErrors(errs); window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
    setErrors([]);

    if (subPhase < totalSubPhases - 1) {
      setSubPhase(s => s + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    // Last sub-phase of this phase: advance to next phase or submit
    if (phase < 3) {
      setPhase(p => p + 1);
      setSubPhase(0);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    // Submit all 3 phases
    await handleSubmit();
  };

  const handleBack = () => {
    setErrors([]);
    if (subPhase > 0) { setSubPhase(s => s - 1); window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
    if (phase > 1) { setPhase(p => p - 1); setSubPhase(PHASES[phase - 2].subPhases.length - 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }
  };

  const handleSubmit = async () => {
    setSaving(true);
    try {
      const payload: VendorProfilePayload = {
        identity,
        geography,
        business_domain: business,
        financials,
        past_project_experience: projects,
        certifications,
        compliance,
        notification_preferences: notifications,
      };
      const result = await vendorProfileService.create(payload);
      setSaved(result);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to save profile. Please try again.';
      setErrors([msg]);
    } finally {
      setSaving(false);
    }
  };

  /* ── Success Screen ──────────────────────────────────────────────────────── */
  if (saved) {
    return (
      <div className="vpf-page">
        <div className="vpf-page-inner">
          <div className="vpf-success">
            <div className="vpf-success-icon">🎉</div>
            <h1 className="vpf-success-title">Vendor Profile Created!</h1>
            <p className="vpf-success-sub">Your profile has been saved successfully.</p>
            {saved.vendor_id && <div className="vpf-success-id">Vendor ID: {saved.vendor_id}</div>}
            <div className="vpf-completeness-bar">
              <div className="vpf-completeness-label">
                <span>Profile Completeness</span>
                <span>{saved.profile_completeness_pct}%</span>
              </div>
              <div className="vpf-completeness-track">
                <div className="vpf-completeness-fill" style={{ width: `${saved.profile_completeness_pct}%` }} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              <button className="vpf-btn-secondary" onClick={() => { setSaved(null); setPhase(1); setSubPhase(0); }}>
                Create Another
              </button>
              <button className="vpf-btn-primary" onClick={() => navigate('/match')}>
                Run AI Match →
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ── Stepper Status ──────────────────────────────────────────────────────── */
  const phaseStatus = (p: number): 'completed' | 'active' | 'pending' => {
    if (p < phase) return 'completed';
    if (p === phase) return 'active';
    return 'pending';
  };

  const isLastStep = phase === 3 && subPhase === totalSubPhases - 1;

  return (
    <div className="vpf-page">
      <div className="vpf-page-inner">

        {/* Page Header */}
        <div className="vpf-page-header">
          <h1 className="vpf-page-title">Vendor Profile Registration</h1>
          <p className="vpf-page-subtitle">
            Complete your vendor profile in 3 phases to unlock AI-powered tender matching
          </p>
        </div>

        {/* Phase Stepper */}
        <div className="vpf-stepper">
          {PHASES.map((ph, idx) => (
            <React.Fragment key={ph.id}>
              <div className={`vpf-step ${phaseStatus(ph.id)}`}>
                <div className="vpf-step-indicator">
                  {phaseStatus(ph.id) === 'completed' ? '✓' : ph.id}
                </div>
                <div className="vpf-step-info">
                  <div className="vpf-step-label">{ph.label}</div>
                  <div className="vpf-step-title">{ph.title}</div>
                </div>
              </div>
              {idx < PHASES.length - 1 && (
                <div className={`vpf-step-connector ${phaseStatus(ph.id) === 'completed' ? 'done' : ''}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Sub-Phase Tabs */}
        <div className="vpf-subtabs">
          {currentPhaseConfig.subPhases.map((sp, idx) => (
            <button key={sp}
              className={`vpf-subtab ${idx === subPhase ? 'active' : ''}`}
              onClick={() => { setErrors([]); setSubPhase(idx); }}>
              {idx < subPhase ? '✓ ' : ''}{sp}
            </button>
          ))}
        </div>

        {/* Validation Errors */}
        {errors.length > 0 && (
          <div className="vpf-alert">
            <span className="vpf-alert-icon">⚠️</span>
            <ul>
              {errors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </div>
        )}

        {/* Active Sub-Phase Form */}
        {renderSubPhase()}

        {/* Navigation */}
        <div className="vpf-nav">
          <div className="vpf-nav-left">
            {(phase > 1 || subPhase > 0) && (
              <button className="vpf-btn-secondary" onClick={handleBack} disabled={saving}>
                ← Back
              </button>
            )}
          </div>
          <div className="vpf-nav-right">
            {saving ? (
              <div className="vpf-saving">
                <div className="vpf-spinner" />
                Saving profile…
              </div>
            ) : (
              <button className="vpf-btn-primary" onClick={handleNext} disabled={saving}>
                {isLastStep ? '🚀 Submit Profile' : 'Next →'}
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
