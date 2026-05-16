import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { FloatingDots } from '../components/FloatingDots';
import { loginUser } from '../services/authService';
import type { Role } from '../types/user';

export const Login = () => {
    const { login } = useAuth();
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (!email || !password) { setError('Please fill all fields.'); return; }
        setLoading(true);
        try {
            const data = await loginUser({ email, password });
            login(data.access_token, {
                id: data.user.id,
                name: data.user.name,
                email: data.user.email,
                role: data.user.role as Role,
                org_id: data.user.org_id,
                preferences: data.user.preferences,
            });
            const role = data.user.role;
            if (role === 'SUPERADMIN') navigate('/admin/organizations');
            else if (role === 'CUSTOMER_SUPPORT') navigate('/support/view/1');
            else navigate('/dashboard');
        } catch (err: any) {
            const msg = err?.response?.data?.detail || 'Login failed. Please check your credentials.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex bg-[#f1f5f9] relative overflow-hidden" style={{ fontFamily: 'DM Sans' }}>
            <FloatingDots />

            {/* Minimal top nav strip */}
            <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4 bg-white/80 backdrop-blur-sm border-b border-slate-200">
                <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-md bg-[#162f3e]">
                        <span className="text-white font-bold text-sm">≡</span>
                    </div>
                    <div>
                        <span className="font-bold text-[#162f3e] text-sm" style={{ fontFamily: 'Poppins' }}>TenderMatch</span>
                        <span className="text-[10px] text-[#c41230] font-medium ml-1.5" style={{ fontFamily: 'DM Sans' }}>Live & Listening!</span>
                    </div>
                </div>
                <div className="hidden md:flex items-center gap-8">
                    {['Services', 'Case Studies', 'Products', 'Company', 'Contact'].map(link => (
                        <a key={link} href="#" className="text-sm text-[#475569] hover:text-[#162f3e] font-medium transition-colors" style={{ fontFamily: 'DM Sans' }}>
                            {link}
                        </a>
                    ))}
                </div>
                <button className="pm-btn-primary text-sm py-2.5 px-5">
                    Resources
                </button>
            </nav>

            {/* Main centered content */}
            <div className="flex-1 flex flex-col items-center justify-center px-4 pt-20 pb-12 z-10">
                {/* Hero headline */}
                <div className="text-center mb-12 max-w-3xl">
                    <p className="pm-badge mb-5">AI-Powered Matching Engine</p>
                    <h1 className="text-5xl md:text-6xl font-bold leading-tight mb-4 text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>
                        Find the Right Tenders
                    </h1>
                    <h1 className="text-5xl md:text-6xl font-bold text-[#c41230] mb-6 leading-tight" style={{ fontFamily: 'Poppins' }}>
                        Win the Right Business
                    </h1>
                    <p className="text-lg text-[#475569] max-w-xl mx-auto leading-relaxed" style={{ fontFamily: 'DM Sans' }}>
                        TenderMatch uses GenAI to intelligently profile vendors, parse tenders, and deliver high-confidence matches — automatically.
                    </p>
                </div>

                {/* Login card */}
                <div className="w-full max-w-md">
                    <div className="bg-white rounded-3xl border border-slate-200 shadow-xl p-8 md:p-10">
                        <div className="mb-8">
                            <h2 className="text-2xl font-bold text-[#162f3e] mb-1" style={{ fontFamily: 'Poppins' }}>Sign In to Portal</h2>
                            <p className="text-sm text-[#475569]" style={{ fontFamily: 'DM Sans' }}>Access your TenderMatch dashboard</p>
                        </div>

                        {error && (
                            <div className="mb-5 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-[#c41230]" style={{ fontFamily: 'DM Sans' }}>
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-5">
                            <div>
                                <label className="block text-xs font-semibold text-[#162f3e] mb-1.5 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Email Address</label>
                                <input
                                    type="email"
                                    required
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    placeholder="you@company.com"
                                    className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-[#162f3e] placeholder:text-slate-400 focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 transition-all bg-slate-50"
                                    style={{ fontFamily: 'DM Sans' }}
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-semibold text-[#162f3e] mb-1.5 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Password</label>
                                <input
                                    type="password"
                                    required
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm text-[#162f3e] placeholder:text-slate-400 focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 transition-all bg-slate-50"
                                    style={{ fontFamily: 'DM Sans' }}
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="pm-btn-primary w-full mt-2 py-3.5 text-base rounded-xl justify-center disabled:opacity-70"
                            >
                                {loading ? 'Signing In…' : (
                                    <>Sign In <ArrowRight className="w-4 h-4" /></>
                                )}
                            </button>
                        </form>

                        <div className="mt-6 text-center">
                            <p className="text-sm text-[#475569]" style={{ fontFamily: 'DM Sans' }}>
                                New organization?{' '}
                                <a href="/register" className="text-[#c41230] font-semibold hover:underline">
                                    Register here
                                </a>
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Decorative right-side dots */}
            <div className="fixed right-5 top-1/2 -translate-y-1/2 flex flex-col gap-2 z-50">
                {[1, 2, 3, 4, 5, 6].map((_, i) => (
                    <div key={i} className={`w-2.5 h-2.5 rounded-full ${i === 0 ? 'bg-[#c41230]' : 'bg-slate-300'}`} />
                ))}
            </div>
        </div>
    );
};
