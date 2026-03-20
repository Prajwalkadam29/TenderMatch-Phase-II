import React from 'react';
import type { GeographyBlock, Address } from '../../types/vendorProfile';
import { INDIAN_STATES } from '../../types/vendorProfile';
import './VendorProfileForm.css';

interface Props {
  data: GeographyBlock;
  onChange: (data: GeographyBlock) => void;
}

const MultiStateSelect: React.FC<{
  label: string; hint?: string; required?: boolean;
  selected: string[]; onChange: (v: string[]) => void;
}> = ({ label, hint, required, selected, onChange }) => {
  const toggle = (s: string) => {
    if (selected.includes(s)) onChange(selected.filter(x => x !== s));
    else onChange([...selected, s]);
  };
  return (
    <div className="vpf-field vpf-field-full">
      <label className="vpf-label">{label} {required && <span className="req">*</span>}</label>
      {hint && <p className="vpf-hint">{hint}</p>}
      <div className="vpf-state-grid">
        {INDIAN_STATES.map(s => (
          <button key={s} type="button"
            className={`vpf-state-chip ${selected.includes(s) ? 'selected' : ''}`}
            onClick={() => toggle(s)}>
            {s}
          </button>
        ))}
      </div>
      {selected.length > 0 && (
        <div className="vpf-selected-count">{selected.length} state(s) selected</div>
      )}
    </div>
  );
};

export const Phase1Geography: React.FC<Props> = ({ data, onChange }) => {
  const set = (field: keyof GeographyBlock, value: unknown) =>
    onChange({ ...data, [field]: value });

  const setAddr = (field: keyof Address, value: string) =>
    onChange({ ...data, registered_office_address: { ...data.registered_office_address, [field]: value } });

  const toggleDistrict = (d: string) => {
    const current = data.operational_districts || [];
    if (current.includes(d)) set('operational_districts', current.filter(x => x !== d));
    else set('operational_districts', [...current, d]);
  };

  return (
    <div className="vpf-phase">
      <div className="vpf-phase-header">
        <span className="vpf-phase-icon">📍</span>
        <div>
          <h2 className="vpf-phase-title">Geography & Locations</h2>
          <p className="vpf-phase-subtitle">Where your company is registered and operates</p>
        </div>
      </div>

      {/* Registered Office */}
      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          Registered Office Address
        </div>
        <div className="vpf-grid-2">
          <div className="vpf-field vpf-field-full">
            <label className="vpf-label">Street Address <span className="req">*</span></label>
            <input className="vpf-input" value={data.registered_office_address?.street || ''}
              placeholder="e.g. Plot 45, Baner Road"
              onChange={e => setAddr('street', e.target.value)} />
          </div>

          <div className="vpf-field">
            <label className="vpf-label">City <span className="req">*</span></label>
            <input className="vpf-input" value={data.registered_office_address?.city || ''}
              placeholder="e.g. Pune"
              onChange={e => setAddr('city', e.target.value)} />
          </div>

          <div className="vpf-field">
            <label className="vpf-label">District <span className="req">*</span></label>
            <input className="vpf-input" value={data.registered_office_address?.district || ''}
              placeholder="e.g. Pune"
              onChange={e => setAddr('district', e.target.value)} />
          </div>

          <div className="vpf-field">
            <label className="vpf-label">State <span className="req">*</span></label>
            <select className="vpf-select" value={data.registered_office_address?.state || ''}
              onChange={e => setAddr('state', e.target.value)}>
              <option value="">Select state…</option>
              {INDIAN_STATES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div className="vpf-field">
            <label className="vpf-label">State Code</label>
            <input className="vpf-input" value={data.registered_office_address?.state_code || ''}
              placeholder="e.g. 27"
              onChange={e => setAddr('state_code', e.target.value)} />
          </div>

          <div className="vpf-field">
            <label className="vpf-label">Pincode <span className="req">*</span></label>
            <input className="vpf-input" value={data.registered_office_address?.pincode || ''}
              placeholder="e.g. 411045"
              onChange={e => setAddr('pincode', e.target.value)} />
          </div>
        </div>
      </div>

      {/* State Selections */}
      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          State Coverage
        </div>

        <MultiStateSelect
          label="GST Registered States"
          hint="States where you hold valid GST registration — primary geo-filter"
          required
          selected={data.registered_states}
          onChange={v => set('registered_states', v)}
        />

        <MultiStateSelect
          label="Operational States"
          hint="States where you have executed work or can execute new projects"
          required
          selected={data.operational_states}
          onChange={v => set('operational_states', v)}
        />
      </div>

      {/* Optional */}
      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-optional-badge">Optional</span>
          Preferences
        </div>

        <MultiStateSelect
          label="Preferred States"
          hint="States you actively want to pursue — boosts notification priority"
          selected={data.preferred_states || []}
          onChange={v => set('preferred_states', v)}
        />

        <div className="vpf-field vpf-field-full">
          <label className="vpf-label">Operational Districts (comma-separated)</label>
          <input className="vpf-input"
            value={(data.operational_districts || []).join(', ')}
            placeholder="e.g. Pune, Nashik, Mumbai, Ahmedabad"
            onChange={e => set('operational_districts', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} />
          <p className="vpf-hint">City/district-level presence improves local tender precision scoring</p>
        </div>

        <div className="vpf-field">
          <label className="vpf-checkbox-label">
            <input type="checkbox"
              checked={data.willing_to_operate_in_new_states || false}
              onChange={e => set('willing_to_operate_in_new_states', e.target.checked)} />
            <span>Willing to operate in new states</span>
          </label>
          <p className="vpf-hint">System will match tenders outside current operational states with a reduced geo score (0.5)</p>
        </div>
      </div>
    </div>
  );
};
