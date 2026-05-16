import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
    User, Mail, Shield, CheckCircle2, 
    AlertCircle, Loader2, Save, Camera
} from 'lucide-react';
import { motion } from 'framer-motion';

export const UserProfile: React.FC = () => {
    const { user, updateProfile } = useAuth();
    
    const [name, setName] = useState(user?.name || '');
    const [email] = useState(user?.email || '');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');

    const handleUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setSuccess(false);
        setError('');
        try {
            await updateProfile({ name });
            setSuccess(true);
            setTimeout(() => setSuccess(false), 3000);
        } catch (err) {
            setError('Failed to update profile settings.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-4xl" style={{ fontFamily: 'DM Sans' }}>
            <div className="mb-10">
                <span className="pm-badge mb-3">Account Intelligence</span>
                <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                    User <span className="text-[#c41230]">Settings</span>
                </h1>
                <p className="text-[#475569] text-base">Manage your personal identity and platform preferences.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-1 space-y-6">
                    <div className="pm-card flex flex-col items-center text-center">
                        <div className="relative mb-6">
                            <div className="w-24 h-24 rounded-3xl bg-[#c41230] flex items-center justify-center text-white text-3xl font-bold shadow-xl shadow-[#c41230]/20" style={{ fontFamily: 'Poppins' }}>
                                {user?.name?.charAt(0).toUpperCase()}
                            </div>
                            <button className="absolute -bottom-2 -right-2 p-2 bg-white border border-[#e2e8f0] rounded-xl shadow-lg text-slate-400 hover:text-[#c41230] transition-all">
                                <Camera className="w-4 h-4" />
                            </button>
                        </div>
                        <h2 className="text-xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>{user?.name}</h2>
                        <p className="text-sm text-[#475569] mt-1">{user?.email}</p>
                        <div className="mt-4 px-3 py-1 rounded-full bg-[#fdf2f2] text-[10px] font-black text-[#c41230] uppercase tracking-widest border border-red-100">
                            {user?.role} Access
                        </div>
                    </div>

                    <div className="pm-card">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Security Status</h3>
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <Shield className="w-4 h-4 text-emerald-500" />
                                <span className="text-xs font-medium text-[#162f3e]">MFA Enabled</span>
                            </div>
                            <div className="flex items-center gap-3">
                                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                                <span className="text-xs font-medium text-[#162f3e]">Account Verified</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="lg:col-span-2 space-y-6">
                    <form onSubmit={handleUpdate} className="pm-card">
                        <div className="flex items-center justify-between mb-8">
                            <h3 className="text-lg font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>Personal Information</h3>
                            <button 
                                type="submit" 
                                disabled={loading}
                                className="pm-btn-primary py-2 px-6 flex items-center gap-2 text-xs"
                            >
                                {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                                SAVE CHANGES
                            </button>
                        </div>

                        {success && (
                            <motion.div 
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="mb-6 p-4 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-2xl flex items-center gap-3 text-sm"
                            >
                                <CheckCircle2 className="w-5 h-5" />
                                Profile updated successfully!
                            </motion.div>
                        )}

                        {error && (
                            <div className="mb-6 p-4 bg-red-50 border border-red-100 text-[#c41230] rounded-2xl flex items-center gap-3 text-sm">
                                <AlertCircle className="w-5 h-5" />
                                {error}
                            </div>
                        )}

                        <div className="space-y-5">
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2 px-1">Display Name</label>
                                <div className="relative">
                                    <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                                    <input 
                                        type="text"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        className="w-full pl-11 pr-4 py-3 bg-[#f8fafc] border border-[#e2e8f0] rounded-2xl text-sm focus:outline-none focus:border-[#c41230] transition-all"
                                        placeholder="Full Name"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2 px-1">Email Address</label>
                                <div className="relative">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                                    <input 
                                        type="email"
                                        value={email}
                                        disabled
                                        className="w-full pl-11 pr-4 py-3 bg-[#f8fafc] border border-[#e2e8f0] rounded-2xl text-sm opacity-60 cursor-not-allowed"
                                    />
                                </div>
                                <p className="mt-2 text-[10px] text-slate-400 italic ml-1">Email cannot be changed without admin verification.</p>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};
