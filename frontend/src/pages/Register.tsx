import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Building2, User } from 'lucide-react';
import { FloatingDots } from '../components/FloatingDots';
import { registerUser } from '../services/authService';
import type { Role } from '../types/user';

export const Register = () => {
    const { login } = useAuth();
    const navigate = useNavigate();

    const [step, setStep] = useState<'role' | 'details'>('role');
    const [selectedRole, setSelectedRole] = useState<'ADMIN1' | 'USER'>('ADMIN1');
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [orgName, setOrgName] = useState('');
    const [orgIndustry, setOrgIndustry] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (!name || !email || !password) { setError('Please fill all required fields.'); return; }
        if (selectedRole === 'ADMIN1' && !orgName) { setError('Organization name is required.'); return; }

        setLoading(true);
        try {
            const data = await registerUser({
                name,
                email,
                password,
                role: selectedRole,
                org_name: selectedRole === 'ADMIN1' ? orgName : undefined,
                org_industry: selectedRole === 'ADMIN1' ? orgIndustry : undefined,
            });
            login(data.access_token, {
                id: data.user.id,
                name: data.user.name,
                email: data.user.email,
                role: data.user.role as Role,
                org_id: data.user.org_id,
            });
            navigate('/dashboard');
        } catch (err: any) {
            const msg = err?.response?.data?.detail || 'Registration failed. Please try again.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex bg-[#f1f5f9] relative overflow-hidden" style={{ fontFamily: 'DM Sans' }}>
            <FloatingDots />

            {/* Navbar */}
            <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4 bg-white/80 backdrop-blur-sm border-b border-slate-200">
                <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-md bg-[#162f3e]">
                        <span className="text-white font-bold text-sm">≡</span>
                    </div>
                    <div>
                        <span className="font-bold text-[#162f3e] text-sm" style={{ fontFamily: 'Poppins' }}>TenderMatch</span>
                        <span className="text-[10px] text-[#c41230] font-medium ml-1.5">Live & Listening!</span>
                    </div>
                </div>
                <a href="/login" className="pm-btn-secondary text-sm py-2.5 px-5">Sign In</a>
            </nav>

            <div className="flex-1 flex flex-col items-center justify-center px-4 pt-20 pb-12 z-10">

                {/* Header */}
                <div className="text-center mb-10 max-w-2xl">
                    <p className="pm-badge mb-5">Get Started Today</p>
                    <h1 className="text-4xl md:text-5xl font-bold text-[#162f3e] mb-3" style={{ fontFamily: 'Poppins' }}>
                        Create Your Account
                    </h1>
                    <p className="text-[#475569] text-base">
                        Join TenderMatch and start winning the right business with AI.
                    </p>
                </div>

                {/* Card */}
                <div className="w-full max-w-lg">
                    <div className="bg-white rounded-3xl border border-slate-200 shadow-xl p-8 md:p-10">

                        {/* Role selection step */}
                        {step === 'role' && (
                            <>
                                <h2 className="text-xl font-bold text-[#162f3e] mb-2" style={{ fontFamily: 'Poppins' }}>Choose your role</h2>
                                <p className="text-sm text-[#475569] mb-6">Are you registering as an organization admin or a team member?</p>

                                <div className="grid grid-cols-1 gap-4 mb-6">
                                    {[
                                        { role: 'ADMIN1' as const, label: 'Organization Admin', desc: 'Create your org and manage your team', icon: Building2 },
                                        { role: 'USER' as const, label: 'Team Member', desc: 'Join an existing organization', icon: User },
                                    ].map(({ role, label, desc, icon: Icon }) => (
                                        <button
                                            key={role}
                                            onClick={() => setSelectedRole(role)}
                                            className={`flex items-center gap-4 p-5 rounded-2xl border-2 transition-all text-left ${
                                                selectedRole === role
                                                    ? 'border-[#c41230] bg-red-50'
                                                    : 'border-slate-200 hover:border-slate-300 bg-slate-50'
                                            }`}
                                        >
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${selectedRole === role ? 'bg-[#c41230]' : 'bg-slate-200'}`}>
                                                <Icon className={`w-5 h-5 ${selectedRole === role ? 'text-white' : 'text-slate-500'}`} />
                                            </div>
                                            <div>
                                                <p className="font-semibold text-[#162f3e] text-sm" style={{ fontFamily: 'Poppins' }}>{label}</p>
                                                <p className="text-xs text-[#475569] mt-0.5">{desc}</p>
                                            </div>
                                        </button>
                                    ))}
                                </div>

                                <button
                                    onClick={() => setStep('details')}
                                    className="pm-btn-primary w-full py-3.5 justify-center"
                                >
                                    Continue <ArrowRight className="w-4 h-4" />
                                </button>
                            </>
                        )}

                        {/* Details step */}
                        {step === 'details' && (
                            <>
                                <div className="flex items-center gap-3 mb-6">
                                    <button onClick={() => setStep('role')} className="text-sm text-[#475569] hover:text-[#162f3e] transition-colors">← Back</button>
                                    <h2 className="text-xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>
                                        {selectedRole === 'ADMIN1' ? 'Register as Admin' : 'Register as User'}
                                    </h2>
                                </div>

                                {error && (
                                    <div className="mb-5 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-[#c41230]">
                                        {error}
                                    </div>
                                )}

                                <form onSubmit={handleSubmit} className="space-y-4">
                                    {/* Org fields — ADMIN1 only */}
                                    {selectedRole === 'ADMIN1' && (
                                        <>
                                            <div>
                                                <label className="block text-xs font-semibold text-[#162f3e] mb-1.5 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Organization Name *</label>
                                                <input
                                                    type="text"
                                                    required
                                                    value={orgName}
                                                    onChange={e => setOrgName(e.target.value)}
                                                    placeholder="Acme Corp"
                                                    className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-[#162f3e] placeholder:text-slate-400 focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 bg-slate-50"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-semibold text-[#162f3e] mb-1.5 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Industry</label>
                                                <select
                                                    value={orgIndustry}
                                                    onChange={e => setOrgIndustry(e.target.value)}
                                                    className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-[#162f3e] focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 bg-slate-50"
                                                >
                                                    <option value="">Select Industry</option>
                                                    {['Technology', 'Construction', 'Healthcare', 'Finance', 'Manufacturing', 'Consulting', 'Education', 'Other'].map(i => (
                                                        <option key={i} value={i}>{i}</option>
                                                    ))}
                                                </select>
                                            </div>
                                        </>
                                    )}

                                    <div>
                                        <label className="block text-xs font-semibold text-[#162f3e] mb-1.5 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Full Name *</label>
                                        <input
                                            type="text"
                                            required
                                            value={name}
                                            onChange={e => setName(e.target.value)}
                                            placeholder="Alex Johnson"
                                            className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-[#162f3e] placeholder:text-slate-400 focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 bg-slate-50"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-xs font-semibold text-[#162f3e] mb-1.5 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Email Address *</label>
                                        <input
                                            type="email"
                                            required
                                            value={email}
                                            onChange={e => setEmail(e.target.value)}
                                            placeholder="you@company.com"
                                            className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-[#162f3e] placeholder:text-slate-400 focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 bg-slate-50"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-xs font-semibold text-[#162f3e] mb-1.5 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Password *</label>
                                        <input
                                            type="password"
                                            required
                                            minLength={8}
                                            value={password}
                                            onChange={e => setPassword(e.target.value)}
                                            placeholder="Min. 8 characters"
                                            className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-[#162f3e] placeholder:text-slate-400 focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 bg-slate-50"
                                        />
                                    </div>

                                    <button
                                        type="submit"
                                        disabled={loading}
                                        className="pm-btn-primary w-full py-3.5 justify-center mt-2 disabled:opacity-70"
                                    >
                                        {loading ? 'Creating Account…' : (<>Create Account <ArrowRight className="w-4 h-4" /></>)}
                                    </button>
                                </form>
                            </>
                        )}

                        <div className="mt-5 text-center">
                            <p className="text-sm text-[#475569]">
                                Already have an account?{' '}
                                <a href="/login" className="text-[#c41230] font-semibold hover:underline">Sign in</a>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
