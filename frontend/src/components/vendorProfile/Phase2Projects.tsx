import React, { useState } from 'react';
import type { PastProjectExperienceBlock, PastProject } from '../../types/vendorProfile';
import { CLIENT_TYPES, WORK_TYPES, INDIAN_STATES } from '../../types/vendorProfile';
import './VendorProfileForm.css';

interface Props {
  data: PastProjectExperienceBlock;
  onChange: (d: PastProjectExperienceBlock) => void;
}

const blankProject = (): PastProject => ({
  project_title: '',
  work_type: '',
  work_description: '',
  contract_value_inr: 0,
  contract_value_excl_gst_inr: undefined,
  client_name: '',
  client_type: '',
  location_state: '',
  location_city: '',
  year_of_completion: new Date().getFullYear(),
  completion_certificate_available: false,
  tds_certificate_available: false,
  work_order_available: false,
  sub_contracted: false,
  remarks: '',
});

export const Phase2Projects: React.FC<Props> = ({ data, onChange }) => {
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState<PastProject>(blankProject());
  const [showForm, setShowForm] = useState(false);

  const setDraftField = (field: keyof PastProject, value: unknown) =>
    setDraft(p => ({ ...p, [field]: value }));

  const saveProject = () => {
    let updated: PastProject[];
    if (editing !== null) {
      updated = data.projects.map((p, i) => i === editing ? draft : p);
    } else {
      updated = [...data.projects, { ...draft, project_id: `PRJ-${String(data.projects.length + 1).padStart(3, '0')}` }];
    }
    const largest = Math.max(...updated.map(p => p.contract_value_inr));
    onChange({ projects: updated, largest_single_project_value_inr: largest });
    setEditing(null);
    setDraft(blankProject());
    setShowForm(false);
  };

  const editProject = (idx: number) => {
    setDraft({ ...data.projects[idx] });
    setEditing(idx);
    setShowForm(true);
  };

  const removeProject = (idx: number) => {
    const updated = data.projects.filter((_, i) => i !== idx);
    const largest = updated.length ? Math.max(...updated.map(p => p.contract_value_inr)) : 0;
    onChange({ projects: updated, largest_single_project_value_inr: largest });
  };

  return (
    <div className="vpf-phase">
      <div className="vpf-phase-header">
        <span className="vpf-phase-icon">📋</span>
        <div>
          <h2 className="vpf-phase-title">Past Project Experience</h2>
          <p className="vpf-phase-subtitle">Add at least one completed project to enable matching</p>
        </div>
      </div>

      {/* Project Cards */}
      {data.projects.length > 0 && (
        <div className="vpf-project-list">
          {data.projects.map((p, i) => (
            <div key={i} className="vpf-project-card">
              <div className="vpc-header">
                <div>
                  <div className="vpc-title">{p.project_title}</div>
                  <div className="vpc-meta">
                    <span className="vpc-badge">{p.work_type}</span>
                    <span className="vpc-client">{p.client_name}</span>
                    <span className="vpc-year">{p.year_of_completion}</span>
                  </div>
                </div>
                <div className="vpc-value">₹{p.contract_value_inr.toLocaleString('en-IN')}</div>
              </div>
              <div className="vpc-certs">
                {p.completion_certificate_available && <span className="cert-tag">✓ Completion Cert</span>}
                {p.tds_certificate_available && <span className="cert-tag">✓ TDS Cert</span>}
                {p.work_order_available && <span className="cert-tag">✓ Work Order</span>}
                {p.sub_contracted && <span className="cert-tag warn">Sub-contracted</span>}
              </div>
              <div className="vpc-actions">
                <button type="button" className="vpf-btn-edit" onClick={() => editProject(i)}>Edit</button>
                <button type="button" className="vpf-btn-remove" onClick={() => removeProject(i)}>Remove</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {!showForm && (
        <button type="button" className="vpf-btn-add-project"
          onClick={() => { setDraft(blankProject()); setEditing(null); setShowForm(true); }}>
          + Add Project
        </button>
      )}

      {showForm && (
        <div className="vpf-project-form">
          <h3 className="vpf-project-form-title">{editing !== null ? 'Edit Project' : 'New Project'}</h3>

          <div className="vpf-grid-2">
            <div className="vpf-field vpf-field-full">
              <label className="vpf-label">Project Title <span className="req">*</span></label>
              <input className="vpf-input" value={draft.project_title}
                placeholder="e.g. NH-48 Highway Widening Project"
                onChange={e => setDraftField('project_title', e.target.value)} />
            </div>

            <div className="vpf-field">
              <label className="vpf-label">Work Type <span className="req">*</span></label>
              <select className="vpf-select" value={draft.work_type}
                onChange={e => setDraftField('work_type', e.target.value)}>
                <option value="">Select type…</option>
                {WORK_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div className="vpf-field">
              <label className="vpf-label">Client Name <span className="req">*</span></label>
              <input className="vpf-input" value={draft.client_name}
                placeholder="e.g. NHAI, Pune Municipal Corporation"
                onChange={e => setDraftField('client_name', e.target.value)} />
            </div>

            <div className="vpf-field">
              <label className="vpf-label">Client Type <span className="req">*</span></label>
              <select className="vpf-select" value={draft.client_type}
                onChange={e => setDraftField('client_type', e.target.value)}>
                <option value="">Select type…</option>
                {CLIENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div className="vpf-field">
              <label className="vpf-label">Contract Value (₹) <span className="req">*</span></label>
              <div className="vpf-inr-input">
                <span className="vpf-inr-prefix">₹</span>
                <input className="vpf-input vpf-input-inr" type="number" min={0}
                  value={draft.contract_value_inr || ''}
                  onChange={e => setDraftField('contract_value_inr', parseFloat(e.target.value) || 0)} />
              </div>
            </div>

            <div className="vpf-field">
              <label className="vpf-label">Year of Completion <span className="req">*</span></label>
              <input className="vpf-input" type="number" min={1990} max={2025}
                value={draft.year_of_completion}
                onChange={e => setDraftField('year_of_completion', parseInt(e.target.value) || 0)} />
            </div>

            <div className="vpf-field">
              <label className="vpf-label">Location State</label>
              <select className="vpf-select" value={draft.location_state || ''}
                onChange={e => setDraftField('location_state', e.target.value)}>
                <option value="">Select state…</option>
                {INDIAN_STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div className="vpf-field">
              <label className="vpf-label">Location City</label>
              <input className="vpf-input" value={draft.location_city || ''}
                placeholder="e.g. Pune"
                onChange={e => setDraftField('location_city', e.target.value)} />
            </div>

            <div className="vpf-field vpf-field-full">
              <label className="vpf-label">Work Description</label>
              <textarea className="vpf-textarea" rows={3}
                value={draft.work_description || ''}
                placeholder="Briefly describe the scope of work…"
                onChange={e => setDraftField('work_description', e.target.value)} />
            </div>

            <div className="vpf-field vpf-field-full">
              <label className="vpf-label vpf-mb8">Documents Available</label>
              <div className="vpf-cert-checks">
                <label className="vpf-checkbox-label">
                  <input type="checkbox" checked={draft.completion_certificate_available}
                    onChange={e => setDraftField('completion_certificate_available', e.target.checked)} />
                  <span>Completion Certificate</span>
                </label>
                <label className="vpf-checkbox-label">
                  <input type="checkbox" checked={draft.tds_certificate_available}
                    onChange={e => setDraftField('tds_certificate_available', e.target.checked)} />
                  <span>TDS Certificate</span>
                </label>
                <label className="vpf-checkbox-label">
                  <input type="checkbox" checked={draft.work_order_available}
                    onChange={e => setDraftField('work_order_available', e.target.checked)} />
                  <span>Work Order Copy</span>
                </label>
                <label className="vpf-checkbox-label">
                  <input type="checkbox" checked={draft.sub_contracted}
                    onChange={e => setDraftField('sub_contracted', e.target.checked)} />
                  <span>Sub-contracted</span>
                </label>
              </div>
            </div>

            <div className="vpf-field vpf-field-full">
              <label className="vpf-label">Remarks</label>
              <input className="vpf-input" value={draft.remarks || ''}
                placeholder="Any notes (e.g. Completion certificate pending from client)"
                onChange={e => setDraftField('remarks', e.target.value)} />
            </div>
          </div>

          <div className="vpf-project-form-actions">
            <button type="button" className="vpf-btn-secondary"
              onClick={() => { setShowForm(false); setEditing(null); }}>Cancel</button>
            <button type="button" className="vpf-btn-primary" onClick={saveProject}>
              {editing !== null ? 'Update Project' : 'Add Project'}
            </button>
          </div>
        </div>
      )}

      {data.largest_single_project_value_inr && (
        <div className="vpf-stat-row">
          <span className="vpf-stat-label">Largest Single Project:</span>
          <span className="vpf-stat-value">₹{data.largest_single_project_value_inr.toLocaleString('en-IN')}</span>
        </div>
      )}
    </div>
  );
};
