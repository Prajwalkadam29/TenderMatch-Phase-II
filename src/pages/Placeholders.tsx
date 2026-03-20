import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Building2, Users as UsersIcon, BarChart2, FileSearch, LifeBuoy, Plus, Trash2, X, ChevronDown } from 'lucide-react';
import { getOrgUsers, createOrgUser, deleteOrgUser, type OrgUser, type CreateUserPayload } from '../services/userService';
import { getOrgProfile, updateOrgProfile, type OrgProfile, type OrgUpdatePayload } from '../services/orgService';

// ─── Reusable Placeholder Page ───────────────────────────────────────────────

const PlaceholderPage = ({
    title, subtitle, badge, icon: Icon, links = [],
}: {
    title: string;
    subtitle: string;
    badge: string;
    icon: React.ElementType;
    links?: { label: string; href: string }[];
}) => (
    <div style={{ fontFamily: 'DM Sans' }}>
        <div className="mb-10">
            <span className="pm-badge mb-3">{badge}</span>
            <div className="flex items-center gap-4 mt-3 mb-2">
                <div className="pm-icon-box w-14 h-14">
                    <Icon className="w-7 h-7" />
                </div>
                <h1 className="text-4xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>{title}</h1>
            </div>
            <p className="text-[#475569] text-base mt-3 max-w-xl">{subtitle}</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map(i => (
                <div key={i} className="pm-card animate-pulse">
                    <div className="w-10 h-10 rounded-xl bg-slate-100 mb-4" />
                    <div className="h-4 bg-slate-100 rounded-full w-3/4 mb-2" />
                    <div className="h-3 bg-slate-100 rounded-full w-1/2 mb-4" />
                    <div className="h-1.5 bg-slate-100 rounded-full w-full mb-1" />
                    <div className="h-1.5 bg-slate-100 rounded-full w-4/5" />
                </div>
            ))}
        </div>
        <div className="mt-10 pt-6 border-t border-slate-200 flex flex-wrap gap-3">
            {links.map(link => (
                <Link key={link.href} to={link.href} className="pm-btn-primary text-sm py-2.5 px-5">
                    {link.label}
                </Link>
            ))}
            <button className="pm-btn-secondary text-sm py-2.5 px-5">
                Expected Outcomes →
            </button>
        </div>
    </div>
);

// ─── Static Placeholder Exports ──────────────────────────────────────────────

export const TenderDetail = () => (
    <PlaceholderPage
        title="Tender Detail"
        subtitle="Detailed tender analysis with AI match score breakdown, eligibility, and evidence pages."
        badge="Document Intelligence & Analysis"
        icon={FileSearch}
        links={[{ label: 'Mark as Interested', href: '/tenders' }]}
    />
);

export const Profile = () => (
    <PlaceholderPage
        title="Vendor Profile"
        subtitle="Manage your vendor information, certifications, categories, and geographic preferences."
        badge="Trusted Foundations for Autonomous AI"
        icon={Building2}
    />
);

export const Analytics = () => (
    <PlaceholderPage
        title="Deep Analytics"
        subtitle="Match accuracy, win ratios, and feedback distribution across your organization."
        badge="Operational Analytics from Logs & Time-Series Data"
        icon={BarChart2}
    />
);

export const Subscriptions = () => (
    <PlaceholderPage
        title="Billing & Subscriptions"
        subtitle="Manage subscription plans, billing cycles, and platform-level configurations."
        badge="Finance Ops & Spend Control"
        icon={BarChart2}
    />
);

export const SupportView = () => (
    <PlaceholderPage
        title="Support View"
        subtitle="Read-only access to organization dashboards. No editing permitted."
        badge="Customer Ops, Service Desk & IT Operations"
        icon={LifeBuoy}
    />
);

// ─── Users Page (Real API) ────────────────────────────────────────────────────

export const Users = () => {
    const [users, setUsers] = useState<OrgUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [deleting, setDeleting] = useState<string | null>(null);

    // Add user form state
    const [form, setForm] = useState<CreateUserPayload>({ name: '', email: '', password: '', role: 'USER' });
    const [formLoading, setFormLoading] = useState(false);
    const [formError, setFormError] = useState('');

    const fetchUsers = async () => {
        setLoading(true);
        setError('');
        try {
            const data = await getOrgUsers();
            setUsers(data);
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Failed to load users.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchUsers(); }, []);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setFormError('');
        setFormLoading(true);
        try {
            await createOrgUser(form);
            setShowModal(false);
            setForm({ name: '', email: '', password: '', role: 'USER' });
            await fetchUsers();
        } catch (err: any) {
            setFormError(err?.response?.data?.detail || 'Failed to create user.');
        } finally {
            setFormLoading(false);
        }
    };

    const handleDelete = async (userId: string) => {
        if (!confirm('Remove this user from your organization?')) return;
        setDeleting(userId);
        try {
            await deleteOrgUser(userId);
            setUsers(prev => prev.filter(u => u.id !== userId));
        } catch (err: any) {
            alert(err?.response?.data?.detail || 'Failed to delete user.');
        } finally {
            setDeleting(null);
        }
    };

    const roleBadge = (role: string) => {
        const colors: Record<string, string> = {
            ADMIN1: 'bg-[#162f3e] text-white',
            USER: 'bg-slate-100 text-[#475569]',
            SUPERADMIN: 'bg-[#c41230] text-white',
        };
        return colors[role] || 'bg-slate-100 text-slate-600';
    };

    return (
        <div style={{ fontFamily: 'DM Sans' }}>
            {/* Header */}
            <div className="mb-8 flex items-start justify-between">
                <div>
                    <span className="pm-badge mb-3">Team Management</span>
                    <div className="flex items-center gap-4 mt-3">
                        <div className="pm-icon-box w-14 h-14"><UsersIcon className="w-7 h-7" /></div>
                        <div>
                            <h1 className="text-4xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>Access Control</h1>
                            <p className="text-[#475569] text-sm mt-1">Manage users within your organization</p>
                        </div>
                    </div>
                </div>
                <button onClick={() => setShowModal(true)} className="pm-btn-primary text-sm py-2.5 px-5 mt-4">
                    <Plus className="w-4 h-4" /> Add User
                </button>
            </div>

            {/* Content */}
            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="pm-card animate-pulse">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="w-10 h-10 rounded-full bg-slate-100" />
                                <div className="flex-1">
                                    <div className="h-4 bg-slate-100 rounded-full w-3/4 mb-2" />
                                    <div className="h-3 bg-slate-100 rounded-full w-1/2" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            ) : error ? (
                <div className="pm-card bg-red-50 border-red-200 text-[#c41230] text-sm p-6">{error}</div>
            ) : users.length === 0 ? (
                <div className="pm-card text-center py-16">
                    <UsersIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-[#162f3e] mb-2" style={{ fontFamily: 'Poppins' }}>No users yet</h3>
                    <p className="text-sm text-[#475569] mb-6">Add your first team member to get started.</p>
                    <button onClick={() => setShowModal(true)} className="pm-btn-primary text-sm py-2.5 px-5">
                        <Plus className="w-4 h-4" /> Add First User
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                    {users.map(user => (
                        <div key={user.id} className="pm-card flex flex-col gap-4">
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-[#162f3e] flex items-center justify-center text-white font-bold text-sm">
                                        {user.name.charAt(0).toUpperCase()}
                                    </div>
                                    <div>
                                        <p className="font-semibold text-[#162f3e] text-sm" style={{ fontFamily: 'Poppins' }}>{user.name}</p>
                                        <p className="text-xs text-[#475569]">{user.email}</p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => handleDelete(user.id)}
                                    disabled={deleting === user.id}
                                    className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-[#c41230] hover:bg-red-50 transition-all disabled:opacity-40"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className={`text-xs font-semibold px-3 py-1 rounded-full ${roleBadge(user.role)}`}>
                                    {user.role}
                                </span>
                                <span className={`text-xs px-2 py-0.5 rounded-full ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                                    {user.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Add User Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4">
                    <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-md p-8">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>Add Team Member</h2>
                            <button onClick={() => { setShowModal(false); setFormError(''); }} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-all">
                                <X className="w-4 h-4 text-slate-500" />
                            </button>
                        </div>

                        {formError && (
                            <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-[#c41230]">{formError}</div>
                        )}

                        <form onSubmit={handleCreate} className="space-y-4">
                            {[
                                { label: 'Full Name', key: 'name', type: 'text', placeholder: 'Alex Johnson' },
                                { label: 'Email Address', key: 'email', type: 'email', placeholder: 'alex@company.com' },
                                { label: 'Password', key: 'password', type: 'password', placeholder: 'Min. 8 characters' },
                            ].map(({ label, key, type, placeholder }) => (
                                <div key={key}>
                                    <label className="block text-xs font-semibold text-[#162f3e] mb-1.5 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>{label}</label>
                                    <input
                                        type={type}
                                        required
                                        placeholder={placeholder}
                                        value={form[key as keyof CreateUserPayload] as string}
                                        onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                                        className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-[#162f3e] placeholder:text-slate-400 focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 bg-slate-50"
                                    />
                                </div>
                            ))}

                            <div>
                                <label className="block text-xs font-semibold text-[#162f3e] mb-1.5 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Role</label>
                                <div className="relative">
                                    <select
                                        value={form.role}
                                        onChange={e => setForm(f => ({ ...f, role: e.target.value as 'USER' | 'ADMIN1' }))}
                                        className="w-full appearance-none border border-slate-200 rounded-xl px-4 py-3 text-sm text-[#162f3e] bg-slate-50 focus:outline-none focus:border-[#c41230]"
                                    >
                                        <option value="USER">User — Team Member</option>
                                        <option value="ADMIN1">Admin — Co-Admin</option>
                                    </select>
                                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                                </div>
                            </div>

                            <div className="flex gap-3 mt-2">
                                <button type="button" onClick={() => setShowModal(false)} className="pm-btn-secondary flex-1 py-3 text-sm justify-center">Cancel</button>
                                <button type="submit" disabled={formLoading} className="pm-btn-primary flex-1 py-3 text-sm justify-center disabled:opacity-70">
                                    {formLoading ? 'Adding…' : 'Add User'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

// ─── Organizations Page (Real API) ───────────────────────────────────────────

export const Organizations = () => {
    const [org, setOrg] = useState<OrgProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [editing, setEditing] = useState(false);
    const [form, setForm] = useState<OrgUpdatePayload>({});
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState('');

    useEffect(() => {
        const fetchOrg = async () => {
            try {
                const data = await getOrgProfile();
                setOrg(data);
                setForm({ name: data.name, industry: data.industry, description: data.description, website: data.website, location: data.location });
            } catch (err: any) {
                setError(err?.response?.data?.detail || 'Failed to load organization.');
            } finally {
                setLoading(false);
            }
        };
        fetchOrg();
    }, []);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaveError('');
        setSaving(true);
        try {
            const updated = await updateOrgProfile(form);
            setOrg(updated);
            setEditing(false);
        } catch (err: any) {
            setSaveError(err?.response?.data?.detail || 'Failed to update organization.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div style={{ fontFamily: 'DM Sans' }}>
            <div className="mb-8">
                <span className="pm-badge mb-3">Platform Core Management</span>
                <div className="flex items-center gap-4 mt-3 mb-2">
                    <div className="pm-icon-box w-14 h-14"><Building2 className="w-7 h-7" /></div>
                    <h1 className="text-4xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>Organization</h1>
                </div>
                <p className="text-[#475569] text-base mt-1 max-w-xl">View and edit your organization profile.</p>
            </div>

            {loading ? (
                <div className="pm-card animate-pulse max-w-2xl">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="mb-4">
                            <div className="h-3 bg-slate-100 rounded-full w-1/4 mb-2" />
                            <div className="h-5 bg-slate-100 rounded-full w-3/4" />
                        </div>
                    ))}
                </div>
            ) : error ? (
                <div className="pm-card bg-red-50 border-red-200 text-[#c41230] text-sm p-6">{error}</div>
            ) : org ? (
                <div className="max-w-2xl">
                    {!editing ? (
                        <div className="pm-card space-y-5">
                            {[
                                { label: 'Organization Name', value: org.name },
                                { label: 'Industry', value: org.industry || '—' },
                                { label: 'Description', value: org.description || '—' },
                                { label: 'Website', value: org.website || '—' },
                                { label: 'Location', value: org.location || '—' },
                            ].map(({ label, value }) => (
                                <div key={label} className="border-b border-slate-100 pb-4 last:border-0 last:pb-0">
                                    <p className="text-xs font-semibold text-[#475569] uppercase tracking-wide mb-1" style={{ fontFamily: 'Poppins' }}>{label}</p>
                                    <p className="text-sm text-[#162f3e] font-medium">{value}</p>
                                </div>
                            ))}
                            <button onClick={() => setEditing(true)} className="pm-btn-primary text-sm py-2.5 px-5 mt-2">
                                Edit Profile
                            </button>
                        </div>
                    ) : (
                        <form onSubmit={handleSave} className="pm-card space-y-5">
                            {saveError && (
                                <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-[#c41230]">{saveError}</div>
                            )}
                            {[
                                { label: 'Organization Name', key: 'name', type: 'text' },
                                { label: 'Industry', key: 'industry', type: 'text' },
                                { label: 'Description', key: 'description', type: 'text' },
                                { label: 'Website', key: 'website', type: 'url' },
                                { label: 'Location', key: 'location', type: 'text' },
                            ].map(({ label, key, type }) => (
                                <div key={key}>
                                    <label className="block text-xs font-semibold text-[#162f3e] mb-1.5 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>{label}</label>
                                    <input
                                        type={type}
                                        value={form[key as keyof OrgUpdatePayload] || ''}
                                        onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                                        className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-[#162f3e] focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 bg-slate-50"
                                    />
                                </div>
                            ))}
                            <div className="flex gap-3">
                                <button type="button" onClick={() => setEditing(false)} className="pm-btn-secondary flex-1 py-3 text-sm justify-center">Cancel</button>
                                <button type="submit" disabled={saving} className="pm-btn-primary flex-1 py-3 text-sm justify-center disabled:opacity-70">
                                    {saving ? 'Saving…' : 'Save Changes'}
                                </button>
                            </div>
                        </form>
                    )}
                </div>
            ) : null}
        </div>
    );
};
