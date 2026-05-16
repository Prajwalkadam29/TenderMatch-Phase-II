import React, { useState } from 'react';
import type { GSTINEntry, IdentityBlock } from '../../types/vendorProfile';
import { REGISTRATION_TYPES, MSME_CATEGORIES } from '../../types/vendorProfile';
import './VendorProfileForm.css';

interface Props {
  data: IdentityBlock;
  onChange: (data: IdentityBlock) => void;
}

const emptyGSTIN: GSTINEntry = { gstin: '', state_code: '', state_name: '', is_primary: false };

export const Phase1Identity: React.FC<Props> = ({ data, onChange }) => {
  const [gstinInput, setGstinInput] = useState<GSTINEntry>(emptyGSTIN);
  const [gstinError, setGstinError] = useState('');

  const set = (field: keyof IdentityBlock, value: unknown) =>
    onChange({ ...data, [field]: value });

  const addGSTIN = () => {
    if (!gstinInput.gstin.trim()) { setGstinError('GSTIN is required'); return; }
    if (!/^\d{2}[A-Z]{5}\d{4}[A-Z]{1}\d[Z][A-Z\d]$/.test(gstinInput.gstin)) {
      setGstinError('Invalid GSTIN format'); return;
    }
    const updated = [...data.gstin_list, { ...gstinInput, is_primary: data.gstin_list.length === 0 }];
    onChange({ ...data, gstin_list: updated });
    setGstinInput(emptyGSTIN);
    setGstinError('');
  };

  const removeGSTIN = (idx: number) => {
    const updated = data.gstin_list.filter((_, i) => i !== idx);
    if (updated.length > 0 && !updated.some(g => g.is_primary)) updated[0].is_primary = true;
    onChange({ ...data, gstin_list: updated });
  };

  const setPrimary = (idx: number) => {
    const updated = data.gstin_list.map((g, i) => ({ ...g, is_primary: i === idx }));
    onChange({ ...data, gstin_list: updated });
  };

  return (
    <div className="vpf-phase">
      <div className="vpf-phase-header">
        <span className="vpf-phase-icon">🏢</span>
        <div>
          <h2 className="vpf-phase-title">Company Identity</h2>
          <p className="vpf-phase-subtitle">Legal registration and compliance details</p>
        </div>
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          Core Identity
        </div>

        <div className="vpf-grid-2">
          <div className="vpf-field">
            <label className="vpf-label">Company Legal Name <span className="req">*</span></label>
            <input className="vpf-input" value={data.company_legal_name}
              placeholder="e.g. TechBuild Infrastructure Solutions Pvt Ltd"
              onChange={e => set('company_legal_name', e.target.value)} />
            <p className="vpf-hint">As registered with MCA/ROC</p>
          </div>

          <div className="vpf-field">
            <label className="vpf-label">Registration Type <span className="req">*</span></label>
            <select className="vpf-select" value={data.registration_type}
              onChange={e => set('registration_type', e.target.value)}>
              <option value="">Select type…</option>
              {REGISTRATION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          <div className="vpf-field">
            <label className="vpf-label">Year of Incorporation <span className="req">*</span></label>
            <input className="vpf-input" type="number" min={1900} max={2025}
              value={data.year_of_incorporation || ''}
              placeholder="e.g. 2010"
              onChange={e => set('year_of_incorporation', parseInt(e.target.value) || 0)} />
          </div>

          <div className="vpf-field">
            <label className="vpf-label">PAN Number <span className="req">*</span></label>
            <input className="vpf-input" value={data.pan_number}
              placeholder="e.g. AABCT3518Q"
              onChange={e => set('pan_number', e.target.value.toUpperCase())} />
            <p className="vpf-hint">Format: AAAAA9999A</p>
          </div>
        </div>
      </div>

      {/* GSTIN Section */}
      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          GST Registrations
        </div>

        {data.gstin_list.length > 0 && (
          <div className="vpf-gstin-list">
            {data.gstin_list.map((g, i) => (
              <div key={i} className={`vpf-gstin-tag ${g.is_primary ? 'primary' : ''}`}>
                <span>{g.gstin}</span>
                <span className="gstin-state">{g.state_name} ({g.state_code})</span>
                {g.is_primary && <span className="gstin-primary-badge">Primary</span>}
                {!g.is_primary && (
                  <button type="button" className="gstin-set-primary" onClick={() => setPrimary(i)}>
                    Set Primary
                  </button>
                )}
                <button type="button" className="gstin-remove" onClick={() => removeGSTIN(i)}>✕</button>
              </div>
            ))}
          </div>
        )}

        <div className="vpf-gstin-add">
          <div className="vpf-grid-4">
            <input className="vpf-input" placeholder="GSTIN (27AAAA...)"
              value={gstinInput.gstin}
              onChange={e => setGstinInput(p => ({ ...p, gstin: e.target.value.toUpperCase() }))} />
            <input className="vpf-input" placeholder="State Code (e.g. 27)"
              value={gstinInput.state_code}
              onChange={e => setGstinInput(p => ({ ...p, state_code: e.target.value }))} />
            <input className="vpf-input" placeholder="State Name"
              value={gstinInput.state_name}
              onChange={e => setGstinInput(p => ({ ...p, state_name: e.target.value }))} />
            <button type="button" className="vpf-btn-add" onClick={addGSTIN}>+ Add</button>
          </div>
          {gstinError && <p className="vpf-error">{gstinError}</p>}
        </div>
      </div>

      {/* Optional Identity */}
      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-optional-badge">Optional</span>
          Additional Registrations
        </div>

        <div className="vpf-grid-2">
          <div className="vpf-field">
            <label className="vpf-label">CIN / LLPIN</label>
            <input className="vpf-input" value={data.cin_llpin || ''}
              placeholder="e.g. U45200MH2010PTC201234"
              onChange={e => set('cin_llpin', e.target.value)} />
          </div>

          <div className="vpf-field">
            <label className="vpf-label">Udyam Registration Number</label>
            <input className="vpf-input" value={data.udyam_registration_number || ''}
              placeholder="e.g. UDYAM-MH-27-0012345"
              onChange={e => set('udyam_registration_number', e.target.value)} />
            <p className="vpf-hint">Unlocks EMD exemption on eligible tenders</p>
          </div>

          <div className="vpf-field">
            <label className="vpf-label">MSME Category</label>
            <select className="vpf-select" value={data.msme_category || ''}
              onChange={e => set('msme_category', e.target.value || undefined)}>
              <option value="">Not Applicable</option>
              {MSME_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div className="vpf-field">
            <label className="vpf-label">NSIC Registration Number</label>
            <input className="vpf-input" value={data.nsic_registration_number || ''}
              placeholder="NSIC registration (if any)"
              onChange={e => set('nsic_registration_number', e.target.value)} />
          </div>

          <div className="vpf-field">
            <label className="vpf-label">GeM Seller ID</label>
            <input className="vpf-input" value={data.gem_seller_id || ''}
              placeholder="GeM portal seller ID (if any)"
              onChange={e => set('gem_seller_id', e.target.value)} />
          </div>

          <div className="vpf-field">
            <label className="vpf-label">DPIIT Recognition Number</label>
            <input className="vpf-input" value={data.dpiit_recognition_number || ''}
              placeholder="DPIIT Startup India number (if any)"
              onChange={e => set('dpiit_recognition_number', e.target.value)} />
          </div>
        </div>
      </div>
    </div>
  );
};
