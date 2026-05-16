import React, { useState } from 'react';
import type { BusinessDomainBlock, FinancialsBlock } from '../../types/vendorProfile';
import { PRIMARY_DOMAINS, NET_WORTH_OPTIONS } from '../../types/vendorProfile';
import './VendorProfileForm.css';

// ── Business Domain ──────────────────────────────────────────────────────────

interface BizProps { data: BusinessDomainBlock; onChange: (d: BusinessDomainBlock) => void; }

export const Phase2BusinessDomain: React.FC<BizProps> = ({ data, onChange }) => {
  const [subDomainInput, setSubDomainInput] = useState('');

  const set = (field: keyof BusinessDomainBlock, value: unknown) =>
    onChange({ ...data, [field]: value });

  const toggleDomain = (d: string) => {
    if (data.primary_domains.includes(d))
      set('primary_domains', data.primary_domains.filter(x => x !== d));
    else set('primary_domains', [...data.primary_domains, d]);
  };

  const addSubDomain = () => {
    const val = subDomainInput.trim();
    if (val && !data.sub_domains.includes(val)) {
      set('sub_domains', [...data.sub_domains, val]);
      setSubDomainInput('');
    }
  };

  const handleSubDomainKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addSubDomain();
    }
  };

  return (
    <div className="vpf-phase">
      <div className="vpf-phase-header">
        <span className="vpf-phase-icon">🏗️</span>
        <div>
          <h2 className="vpf-phase-title">Business Domain</h2>
          <p className="vpf-phase-subtitle">What sectors and services you operate in</p>
        </div>
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          Primary Domains
        </div>
        <div className="vpf-domain-grid">
          {PRIMARY_DOMAINS.map(d => (
            <button key={d} type="button"
              className={`vpf-domain-chip ${data.primary_domains.includes(d) ? 'selected' : ''}`}
              onClick={() => toggleDomain(d)}>
              {d}
            </button>
          ))}
        </div>
        <p className="vpf-hint vpf-mt8">Select all sectors that apply — used for hard domain filtering</p>
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          Sub-Domains / Specializations
        </div>
        <div className="vpf-tag-display">
          {data.sub_domains.map((s, i) => (
            <span key={i} className="vpf-tag">
              {s}
              <button type="button" onClick={() => set('sub_domains', data.sub_domains.filter((_, j) => j !== i))}>✕</button>
            </span>
          ))}
        </div>
        <div className="vpf-subdomain-row vpf-mt8">
          <input
            className="vpf-input"
            value={subDomainInput}
            placeholder="e.g. Bridge and flyover construction"
            onChange={e => setSubDomainInput(e.target.value)}
            onKeyDown={handleSubDomainKeyDown}
          />
          <button type="button" className="vpf-btn-add" onClick={addSubDomain}
            style={{ whiteSpace: 'nowrap' }}>
            + Add
          </button>
        </div>
        <p className="vpf-hint">Each specialization is embedded via sentence-transformer for semantic matching</p>
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-optional-badge">Optional</span>
          Capability Description <span className="vpf-high-value-badge">High Value</span>
        </div>
        <textarea className="vpf-textarea" rows={5}
          value={data.capability_description_freetext || ''}
          placeholder="Describe your company's capabilities, expertise, and track record in detail. More detail = better AI match quality."
          onChange={e => set('capability_description_freetext', e.target.value)} />
        <p className="vpf-hint">This text is embedded via AI for deep semantic matching. Aim for 100+ words.</p>
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-optional-badge">Optional</span>
          Tender Value Preference
        </div>
        <div className="vpf-grid-2">
          <div className="vpf-field">
            <label className="vpf-label">Minimum Tender Value (₹)</label>
            <input className="vpf-input" type="number" min={0}
              value={data.tender_value_range_preference?.min_inr || ''}
              placeholder="e.g. 500000"
              onChange={e => set('tender_value_range_preference', {
                ...(data.tender_value_range_preference || { currency: 'INR' }),
                min_inr: parseFloat(e.target.value) || undefined
              })} />
          </div>
          <div className="vpf-field">
            <label className="vpf-label">Maximum Tender Value (₹)</label>
            <input className="vpf-input" type="number" min={0}
              value={data.tender_value_range_preference?.max_inr || ''}
              placeholder="e.g. 500000000"
              onChange={e => set('tender_value_range_preference', {
                ...(data.tender_value_range_preference || { currency: 'INR' }),
                max_inr: parseFloat(e.target.value) || undefined
              })} />
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Financials ──────────────────────────────────────────────────────────────

interface FinProps { data: FinancialsBlock; onChange: (d: FinancialsBlock) => void; }

const CURRENT_FY = ['2024-25', '2023-24', '2022-23'];

export const Phase2Financials: React.FC<FinProps> = ({ data, onChange }) => {
  const set = (field: keyof FinancialsBlock, value: unknown) =>
    onChange({ ...data, [field]: value });

  const setTurnover = (fy: string, val: string) => {
    const existing = data.turnover_by_year || [];
    const updated = existing.filter(t => t.financial_year !== fy);
    if (val) updated.push({ financial_year: fy, turnover_inr: parseFloat(val) });
    set('turnover_by_year', updated.sort((a, b) => b.financial_year.localeCompare(a.financial_year)));
  };

  const getTurnover = (fy: string) =>
    data.turnover_by_year?.find(t => t.financial_year === fy)?.turnover_inr?.toString() || '';

  return (
    <div className="vpf-phase">
      <div className="vpf-phase-header">
        <span className="vpf-phase-icon">💰</span>
        <div>
          <h2 className="vpf-phase-title">Financial Information</h2>
          <p className="vpf-phase-subtitle">Turnover, net worth, and compliance registrations</p>
        </div>
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          Core Financials
        </div>
        <div className="vpf-grid-2">
          <div className="vpf-field vpf-field-full">
            <label className="vpf-label">Average Annual Turnover (Last 3 FY) ₹ <span className="req">*</span></label>
            <div className="vpf-inr-input">
              <span className="vpf-inr-prefix">₹</span>
              <input className="vpf-input vpf-input-inr" type="number" min={0}
                value={data.avg_annual_turnover_inr || ''}
                placeholder="e.g. 62000000"
                onChange={e => set('avg_annual_turnover_inr', parseFloat(e.target.value) || 0)} />
            </div>
            {data.avg_annual_turnover_inr > 0 && (
              <p className="vpf-hint vpf-computed">
                Max advisable tender value: <strong>₹{(data.avg_annual_turnover_inr * 3).toLocaleString('en-IN')}</strong> (3× rule)
              </p>
            )}
          </div>

          <div className="vpf-field">
            <label className="vpf-label">Net Worth Status <span className="req">*</span></label>
            <select className="vpf-select" value={data.net_worth_status}
              onChange={e => set('net_worth_status', e.target.value)}>
              <option value="">Select…</option>
              {NET_WORTH_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </div>

          <div className="vpf-field">
            <label className="vpf-checkbox-label">
              <input type="checkbox"
                checked={data.solvency_certificate_available}
                onChange={e => set('solvency_certificate_available', e.target.checked)} />
              <span>Solvency Certificate Available <span className="req">*</span></span>
            </label>
          </div>

          {data.solvency_certificate_available && (
            <div className="vpf-field">
              <label className="vpf-label">Solvency Bank Name</label>
              <input className="vpf-input" value={data.solvency_bank_name || ''}
                placeholder="e.g. State Bank of India"
                onChange={e => set('solvency_bank_name', e.target.value)} />
            </div>
          )}
        </div>
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-optional-badge">Optional</span>
          Year-wise Turnover Breakdown
        </div>
        <p className="vpf-hint vpf-mb12">Required for tenders that check individual years, not averages</p>
        {CURRENT_FY.map(fy => (
          <div key={fy} className="vpf-grid-2 vpf-mb8">
            <label className="vpf-label vpf-fy-label">{fy}</label>
            <div className="vpf-inr-input">
              <span className="vpf-inr-prefix">₹</span>
              <input className="vpf-input vpf-input-inr" type="number" min={0}
                value={getTurnover(fy)} placeholder="Turnover in INR"
                onChange={e => setTurnover(fy, e.target.value)} />
            </div>
          </div>
        ))}
      </div>

      <div className="vpf-section">
        <div className="vpf-section-label">
          <span className="vpf-required-badge">Required</span>
          Statutory Registrations
        </div>
        <div className="vpf-grid-2">
          <div className="vpf-field">
            <label className="vpf-label">ESI Registration Number <span className="req">*</span></label>
            <input className="vpf-input" value={data.esi_registration_number || ''}
              placeholder="e.g. 31-12345-101"
              onChange={e => set('esi_registration_number', e.target.value)} />
          </div>
          <div className="vpf-field">
            <label className="vpf-label">PF Registration Number <span className="req">*</span></label>
            <input className="vpf-input" value={data.pf_registration_number || ''}
              placeholder="e.g. MH/PUN/0012345"
              onChange={e => set('pf_registration_number', e.target.value)} />
          </div>
        </div>
      </div>
    </div>
  );
};
