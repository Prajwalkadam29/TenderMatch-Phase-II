import React, { useState } from 'react';
import type {
  CertificationsBlock, ComplianceBlock, NotificationPreferencesBlock,
  ISOCertification, DomainLicense,
} from '../../types/vendorProfile';
import { NOTIFICATION_CHANNELS, NOTIFICATION_FREQUENCIES } from '../../types/vendorProfile';
import './VendorProfileForm.css';

// ── Certifications ────────────────────────────────────────────────────────────

interface CertProps { data: CertificationsBlock; onChange: (d: CertificationsBlock) => void; }

const blankISO = (): ISOCertification => ({ standard: '', category: '', certifying_body: '', valid_until: '', certificate_number: '' });
const blankLicense = (): DomainLicense => ({ license_type: '', license_number: '', issuing_authority: '', valid_until: '', applicable_domain: '' });

export const Phase3Certifications: React.FC<CertProps> = ({ data, onChange }) => {
  const [isoForm, setIsoForm] = useState(blankISO());
  const [licForm, setLicForm] = useState(blankLicense());
  const [showIso, setShowIso] = useState(false);
  const [showLic, setShowLic] = useState(false);

  const addISO = () => {
    if (!isoForm.standard.trim()) return;
    onChange({ ...data, iso_certifications: [...data.iso_certifications, isoForm] });
    setIsoForm(blankISO()); setShowIso(false);
  };

  const removeISO = (i: number) =>
    onChange({ ...data, iso_certifications: data.iso_certifications.filter((_, j) => j !== i) });

  const addLicense = () => {
    if (!licForm.license_type.trim()) return;
    onChange({ ...data, domain_licenses: [...data.domain_licenses, licForm] });
    setLicForm(blankLicense()); setShowLic(false);
  };

  const removeLicense = (i: number) =>
    onChange({ ...data, domain_licenses: data.domain_licenses.filter((_, j) => j !== i) });

  return (
    <div className="vpf-phase">
      <div className="vpf-phase-header">
        <span className="vpf-phase-icon">🏅</span>
        <div>
          <h2 className="vpf-phase-title">Certifications & Licenses</h2>
          <p className="vpf-phase-subtitle">ISO standards, domain licenses, and accreditations</p>
        </div>
      </div>

      {/* ISO Certifications */}
      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          ISO Certifications (can be empty)
        </div>

        {data.iso_certifications.map((cert, i) => (
          <div key={i} className="vpf-cert-row">
            <span className="cert-std">{cert.standard}</span>
            <span className="cert-by">{cert.certifying_body}</span>
            <span className="cert-exp">Expires: {cert.valid_until || '—'}</span>
            <button type="button" className="vpf-btn-remove-sm" onClick={() => removeISO(i)}>✕</button>
          </div>
        ))}

        {!showIso ? (
          <button type="button" className="vpf-btn-add" onClick={() => setShowIso(true)}>+ Add ISO Certification</button>
        ) : (
          <div className="vpf-inline-form">
            <div className="vpf-grid-2">
              <div className="vpf-field">
                <label className="vpf-label">Standard <span className="req">*</span></label>
                <input className="vpf-input" value={isoForm.standard}
                  placeholder="e.g. ISO 9001:2015"
                  onChange={e => setIsoForm(p => ({ ...p, standard: e.target.value }))} />
              </div>
              <div className="vpf-field">
                <label className="vpf-label">Category</label>
                <input className="vpf-input" value={isoForm.category || ''}
                  placeholder="e.g. Quality Management System"
                  onChange={e => setIsoForm(p => ({ ...p, category: e.target.value }))} />
              </div>
              <div className="vpf-field">
                <label className="vpf-label">Certifying Body</label>
                <input className="vpf-input" value={isoForm.certifying_body || ''}
                  placeholder="e.g. Bureau Veritas"
                  onChange={e => setIsoForm(p => ({ ...p, certifying_body: e.target.value }))} />
              </div>
              <div className="vpf-field">
                <label className="vpf-label">Valid Until</label>
                <input className="vpf-input" type="date" value={isoForm.valid_until || ''}
                  onChange={e => setIsoForm(p => ({ ...p, valid_until: e.target.value }))} />
              </div>
              <div className="vpf-field">
                <label className="vpf-label">Certificate Number</label>
                <input className="vpf-input" value={isoForm.certificate_number || ''}
                  placeholder="Certificate number"
                  onChange={e => setIsoForm(p => ({ ...p, certificate_number: e.target.value }))} />
              </div>
            </div>
            <div className="vpf-inline-actions">
              <button type="button" className="vpf-btn-secondary" onClick={() => setShowIso(false)}>Cancel</button>
              <button type="button" className="vpf-btn-primary" onClick={addISO}>Save</button>
            </div>
          </div>
        )}
      </div>

      {/* Domain Licenses */}
      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          Domain Licenses (can be empty)
        </div>

        {data.domain_licenses.map((lic, i) => (
          <div key={i} className="vpf-cert-row">
            <span className="cert-std">{lic.license_type}</span>
            <span className="cert-by">{lic.issuing_authority}</span>
            <span className="cert-exp">Expires: {lic.valid_until || '—'}</span>
            <button type="button" className="vpf-btn-remove-sm" onClick={() => removeLicense(i)}>✕</button>
          </div>
        ))}

        {!showLic ? (
          <button type="button" className="vpf-btn-add" onClick={() => setShowLic(true)}>+ Add License</button>
        ) : (
          <div className="vpf-inline-form">
            <div className="vpf-grid-2">
              <div className="vpf-field">
                <label className="vpf-label">License Type <span className="req">*</span></label>
                <input className="vpf-input" value={licForm.license_type}
                  placeholder="e.g. NSIC Registration"
                  onChange={e => setLicForm(p => ({ ...p, license_type: e.target.value }))} />
              </div>
              <div className="vpf-field">
                <label className="vpf-label">License Number</label>
                <input className="vpf-input" value={licForm.license_number || ''}
                  onChange={e => setLicForm(p => ({ ...p, license_number: e.target.value }))} />
              </div>
              <div className="vpf-field">
                <label className="vpf-label">Issuing Authority</label>
                <input className="vpf-input" value={licForm.issuing_authority || ''}
                  placeholder="e.g. National Small Industries Corporation"
                  onChange={e => setLicForm(p => ({ ...p, issuing_authority: e.target.value }))} />
              </div>
              <div className="vpf-field">
                <label className="vpf-label">Valid Until</label>
                <input className="vpf-input" type="date" value={licForm.valid_until || ''}
                  onChange={e => setLicForm(p => ({ ...p, valid_until: e.target.value }))} />
              </div>
              <div className="vpf-field">
                <label className="vpf-label">Applicable Domain</label>
                <input className="vpf-input" value={licForm.applicable_domain || ''}
                  placeholder="e.g. Civil & Construction"
                  onChange={e => setLicForm(p => ({ ...p, applicable_domain: e.target.value }))} />
              </div>
            </div>
            <div className="vpf-inline-actions">
              <button type="button" className="vpf-btn-secondary" onClick={() => setShowLic(false)}>Cancel</button>
              <button type="button" className="vpf-btn-primary" onClick={addLicense}>Save</button>
            </div>
          </div>
        )}
      </div>

      {/* Optional */}
      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-optional-badge">Optional</span>
          Other
        </div>
        <label className="vpf-checkbox-label">
          <input type="checkbox"
            checked={data.mnre_empanelment || false}
            onChange={e => onChange({ ...data, mnre_empanelment: e.target.checked })} />
          <span>MNRE Empanelment (for solar/renewable energy tenders)</span>
        </label>
      </div>
    </div>
  );
};

// ── Compliance ────────────────────────────────────────────────────────────────

interface CompProps { data: ComplianceBlock; onChange: (d: ComplianceBlock) => void; }

export const Phase3Compliance: React.FC<CompProps> = ({ data, onChange }) => {
  const set = (field: keyof ComplianceBlock, value: boolean) =>
    onChange({ ...data, [field]: value });

  return (
    <div className="vpf-phase">
      <div className="vpf-phase-header">
        <span className="vpf-phase-icon">✅</span>
        <div>
          <h2 className="vpf-phase-title">Compliance Declarations</h2>
          <p className="vpf-phase-subtitle">Self-declarations required for tender eligibility</p>
        </div>
      </div>

      <div className="vpf-section">
        <div className="vpf-compliance-grid">
          <div className={`vpf-compliance-card ${data.blacklisted_or_debarred ? 'danger' : 'safe'}`}>
            <div className="compliance-icon">{data.blacklisted_or_debarred ? '🚫' : '✅'}</div>
            <div className="compliance-info">
              <div className="compliance-title">Blacklisted / Debarred <span className="req">*</span></div>
              <div className="compliance-desc">Self-declaration. If true, vendor is filtered from all matches.</div>
            </div>
            <label className="vpf-toggle">
              <input type="checkbox" checked={data.blacklisted_or_debarred}
                onChange={e => set('blacklisted_or_debarred', e.target.checked)} />
              <span className="vpf-toggle-slider" />
            </label>
          </div>

          <div className="vpf-compliance-card safe">
            <div className="compliance-icon">{data.active_litigation ? '⚠️' : '✅'}</div>
            <div className="compliance-info">
              <div className="compliance-title">Active Litigation</div>
              <div className="compliance-desc">Many tenders require declaration of no pending litigation.</div>
            </div>
            <label className="vpf-toggle">
              <input type="checkbox" checked={data.active_litigation || false}
                onChange={e => set('active_litigation', e.target.checked)} />
              <span className="vpf-toggle-slider" />
            </label>
          </div>

          <div className="vpf-compliance-card safe">
            <div className="compliance-icon">{data.gst_returns_compliant ? '✅' : '⚠️'}</div>
            <div className="compliance-info">
              <div className="compliance-title">GST Returns Compliant</div>
              <div className="compliance-desc">Regular GST filer. Required for port, railway, central PSU tenders.</div>
            </div>
            <label className="vpf-toggle">
              <input type="checkbox" checked={data.gst_returns_compliant ?? true}
                onChange={e => set('gst_returns_compliant', e.target.checked)} />
              <span className="vpf-toggle-slider" />
            </label>
          </div>

          <div className="vpf-compliance-card safe">
            <div className="compliance-icon">{data.epf_esic_compliant ? '✅' : '⚠️'}</div>
            <div className="compliance-info">
              <div className="compliance-title">EPF & ESIC Compliant</div>
              <div className="compliance-desc">Compliance with EPF & ESIC filing requirements.</div>
            </div>
            <label className="vpf-toggle">
              <input type="checkbox" checked={data.epf_esic_compliant ?? true}
                onChange={e => set('epf_esic_compliant', e.target.checked)} />
              <span className="vpf-toggle-slider" />
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Notification Preferences ──────────────────────────────────────────────────

interface NotifProps { data: NotificationPreferencesBlock; onChange: (d: NotificationPreferencesBlock) => void; }

export const Phase3Notifications: React.FC<NotifProps> = ({ data, onChange }) => {
  const set = (field: keyof NotificationPreferencesBlock, value: unknown) =>
    onChange({ ...data, [field]: value });

  const toggleChannel = (ch: string) => {
    if (data.preferred_channels.includes(ch))
      set('preferred_channels', data.preferred_channels.filter(c => c !== ch));
    else set('preferred_channels', [...data.preferred_channels, ch]);
  };

  return (
    <div className="vpf-phase">
      <div className="vpf-phase-header">
        <span className="vpf-phase-icon">🔔</span>
        <div>
          <h2 className="vpf-phase-title">Notification Preferences</h2>
          <p className="vpf-phase-subtitle">How and when to receive tender alerts</p>
        </div>
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          Alert Channels
        </div>
        <div className="vpf-channel-grid">
          {NOTIFICATION_CHANNELS.map(ch => (
            <button key={ch} type="button"
              className={`vpf-channel-chip ${data.preferred_channels.includes(ch) ? 'selected' : ''}`}
              onClick={() => toggleChannel(ch)}>
              {ch === 'email' ? '📧' : ch === 'whatsapp' ? '💬' : '📱'} {ch.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="vpf-section">
        <div className="vpf-grid-2">
          <div className="vpf-field vpf-field-full">
            <label className="vpf-label">Email Address <span className="req">*</span></label>
            <input className="vpf-input" type="email" value={data.email}
              placeholder="procurement@company.in"
              onChange={e => set('email', e.target.value)} />
          </div>

          {data.preferred_channels.includes('whatsapp') && (
            <div className="vpf-field">
              <label className="vpf-label">WhatsApp Number</label>
              <input className="vpf-input" value={data.whatsapp_number || ''}
                placeholder="+919876543210"
                onChange={e => set('whatsapp_number', e.target.value)} />
            </div>
          )}

          {data.preferred_channels.includes('sms') && (
            <div className="vpf-field">
              <label className="vpf-label">SMS Number</label>
              <input className="vpf-input" value={data.sms_number || ''}
                placeholder="+919876543210"
                onChange={e => set('sms_number', e.target.value)} />
            </div>
          )}
        </div>
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          Match Threshold
        </div>
        <div className="vpf-slider-wrap">
          <div className="vpf-slider-labels">
            <span>Minimum Match Score: <strong>{Math.round(data.minimum_match_score_threshold * 100)}%</strong></span>
            <span className="vpf-hint">No alerts sent below this score</span>
          </div>
          <input type="range" min={0} max={1} step={0.05}
            className="vpf-slider"
            value={data.minimum_match_score_threshold}
            onChange={e => set('minimum_match_score_threshold', parseFloat(e.target.value))} />
          <div className="vpf-slider-range">
            <span>0%</span><span>50%</span><span>100%</span>
          </div>
        </div>
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-optional-badge">Optional</span>
          Frequency & Filters
        </div>
        <div className="vpf-grid-2">
          <div className="vpf-field">
            <label className="vpf-label">Notification Frequency</label>
            <select className="vpf-select" value={data.notification_frequency || 'realtime'}
              onChange={e => set('notification_frequency', e.target.value)}>
              {NOTIFICATION_FREQUENCIES.map(f => <option key={f} value={f}>{f.replace('_', ' ')}</option>)}
            </select>
          </div>

          <div className="vpf-field">
            <label className="vpf-label">Min Days to Deadline</label>
            <input className="vpf-input" type="number" min={1} max={90}
              value={data.min_days_to_deadline || ''}
              placeholder="e.g. 7"
              onChange={e => set('min_days_to_deadline', parseInt(e.target.value) || undefined)} />
            <p className="vpf-hint">Don't alert on tenders closer than N days to deadline</p>
          </div>
        </div>
      </div>
    </div>
  );
};
