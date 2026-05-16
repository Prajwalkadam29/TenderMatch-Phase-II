import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
    Plus, Search, Filter, MoreVertical, Edit2, 
    Copy, Trash2, Eye, ChevronRight, AlertCircle, 
    CheckCircle2, X, Info, Calendar, Building2,
    MapPin, ArrowUpRight, BarChart3, Loader2
} from 'lucide-react';
import { vendorProfileService } from '../services/vendorProfileApi';
import type { VendorProfileResponse, CompletenessDetail } from '../types/vendorProfile';
import { motion, AnimatePresence } from 'framer-motion';

export const MyProfiles: React.FC = () => {
    const navigate = useNavigate();
    const [profiles, setProfiles] = useState<VendorProfileResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedProfile, setSelectedProfile] = useState<VendorProfileResponse | null>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [actionMenuId, setActionMenuId] = useState<string | null>(null);

    const fetchProfiles = async () => {
        setLoading(true);
        try {
            const data = await vendorProfileService.list();
            // Sort by updated_at desc
            setProfiles(data.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()));
        } catch (err) {
            console.error('Failed to fetch profiles', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProfiles();
    }, []);

    const handleDelete = async (id: string) => {
        if (!window.confirm('Are you sure you want to delete this profile?')) return;
        try {
            await vendorProfileService.delete(id);
            setProfiles(prev => prev.filter(p => p.id !== id));
        } catch (err) {
            alert('Failed to delete profile');
        }
    };

    const handleDuplicate = async (id: string) => {
        try {
            await vendorProfileService.duplicate(id);
            fetchProfiles();
        } catch (err) {
            alert('Failed to duplicate profile');
        }
    };

    const filteredProfiles = profiles.filter(p => 
        p.identity.company_legal_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.business_domain.primary_domains.some(d => d.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    const getStatusColor = (pct: number) => {
        if (pct >= 90) return 'text-emerald-600 bg-emerald-50 border-emerald-100';
        if (pct >= 60) return 'text-amber-600 bg-amber-50 border-amber-100';
        return 'text-[#c41230] bg-red-50 border-red-100';
    };

    return (
        <div className="min-h-screen pb-20" style={{ fontFamily: 'DM Sans' }}>
            {/* Header Area */}
            <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                    <span className="pm-badge mb-3">Profile Management</span>
                    <h1 className="text-4xl font-bold text-[#162f3e] mt-2" style={{ fontFamily: 'Poppins' }}>My Profiles</h1>
                    <p className="text-[#475569] text-base mt-2 max-w-xl">
                        Manage multiple vendor entities and specialized business profiles for targeted AI matching.
                    </p>
                </div>
                <button 
                    onClick={() => navigate('/vendor-profile')}
                    className="pm-btn-primary flex items-center gap-2 py-3 px-6 shadow-lg shadow-[#c41230]/20"
                >
                    <Plus className="w-5 h-5" />
                    <span>Create New Profile</span>
                </button>
            </div>

            {/* Filters Bar */}
            <div className="mb-8 flex flex-col sm:row sm:items-center gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input 
                        type="text"
                        placeholder="Search by business name or sector..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-2xl text-sm focus:outline-none focus:border-[#c41230] focus:ring-4 focus:ring-[#c41230]/5 transition-all"
                    />
                </div>
                <div className="flex items-center gap-3">
                    <button className="flex items-center gap-2 px-4 py-3 bg-white border border-slate-200 rounded-2xl text-sm font-medium text-[#475569] hover:border-[#162f3e] transition-colors">
                        <Filter className="w-4 h-4" />
                        Filter
                    </button>
                    <div className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-2">
                        {filteredProfiles.length} Profiles Found
                    </div>
                </div>
            </div>

            {/* Grid */}
            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="pm-card h-64 animate-pulse bg-slate-50/50" />
                    ))}
                </div>
            ) : filteredProfiles.length === 0 ? (
                <div className="pm-card py-20 text-center flex flex-col items-center border-dashed border-2">
                    <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mb-6">
                        <Building2 className="w-10 h-10 text-slate-300" />
                    </div>
                    <h3 className="text-xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>No profiles found</h3>
                    <p className="text-[#475569] mt-2 mb-8 max-w-xs mx-auto">
                        {searchTerm ? "We couldn't find any profiles matching your search." : "You haven't created any vendor profiles yet."}
                    </p>
                    {!searchTerm && (
                        <button onClick={() => navigate('/vendor-profile')} className="pm-btn-primary py-3 px-8">
                            Get Started
                        </button>
                    )}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredProfiles.map((p) => (
                        <div key={p.id} className="pm-card group relative flex flex-col h-full hover:border-[#c41230]/30 transition-all duration-300">
                            {/* Card Header */}
                            <div className="flex items-start justify-between mb-5">
                                <div className={`px-3 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wider ${getStatusColor(p.profile_completeness_pct)}`}>
                                    {p.profile_completeness_pct}% Complete
                                </div>
                                <div className="relative">
                                    <button 
                                        onClick={() => setActionMenuId(actionMenuId === p.id ? null : p.id)}
                                        className="p-2 rounded-lg hover:bg-slate-50 text-slate-400 transition-colors"
                                    >
                                        <MoreVertical className="w-4 h-4" />
                                    </button>
                                    
                                    <AnimatePresence>
                                        {actionMenuId === p.id && (
                                            <>
                                                <div className="fixed inset-0 z-30" onClick={() => setActionMenuId(null)} />
                                                <motion.div 
                                                    initial={{ opacity: 0, scale: 0.95, y: -10 }}
                                                    animate={{ opacity: 1, scale: 1, y: 0 }}
                                                    exit={{ opacity: 0, scale: 0.95, y: -10 }}
                                                    className="absolute right-0 mt-2 w-48 bg-white border border-slate-100 rounded-xl shadow-xl z-40 overflow-hidden py-1"
                                                >
                                                    <button onClick={() => navigate(`/vendor-profile/${p.id}/edit`)} className="w-full flex items-center gap-3 px-4 py-2.5 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-[#c41230] transition-colors">
                                                        <Edit2 className="w-4 h-4" /> Edit Profile
                                                    </button>
                                                    <button onClick={() => handleDuplicate(p.id)} className="w-full flex items-center gap-3 px-4 py-2.5 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-[#c41230] transition-colors">
                                                        <Copy className="w-4 h-4" /> Duplicate
                                                    </button>
                                                    <div className="h-px bg-slate-50 my-1" />
                                                    <button onClick={() => handleDelete(p.id)} className="w-full flex items-center gap-3 px-4 py-2.5 text-xs font-medium text-[#c41230] hover:bg-red-50 transition-colors">
                                                        <Trash2 className="w-4 h-4" /> Delete
                                                    </button>
                                                </motion.div>
                                            </>
                                        )}
                                    </AnimatePresence>
                                </div>
                            </div>

                            {/* Business Info */}
                            <div className="flex-1">
                                <h3 className="text-lg font-bold text-[#162f3e] mb-1 line-clamp-1" style={{ fontFamily: 'Poppins' }}>
                                    {p.identity.company_legal_name}
                                </h3>
                                <div className="flex items-center gap-1.5 text-xs text-[#475569] mb-4">
                                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                                    <span>{p.geography.registered_office_address?.city}, {p.geography.registered_office_address?.state}</span>
                                </div>

                                {/* Tags */}
                                <div className="flex flex-wrap gap-2 mb-6">
                                    {p.business_domain.primary_domains.slice(0, 2).map(d => (
                                        <span key={d} className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 text-[10px] font-bold">
                                            {d}
                                        </span>
                                    ))}
                                    {p.business_domain.primary_domains.length > 2 && (
                                        <span className="px-2 py-0.5 rounded-md bg-slate-50 text-slate-400 text-[10px] font-bold">
                                            +{p.business_domain.primary_domains.length - 2} More
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* Completeness Preview */}
                            <div className="mb-6">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Strength</span>
                                    <button 
                                        onClick={() => { setSelectedProfile(p); setIsDrawerOpen(true); }}
                                        className="text-[10px] font-bold text-[#c41230] hover:underline flex items-center gap-1"
                                    >
                                        Analyze <Info className="w-3 h-3" />
                                    </button>
                                </div>
                                <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <motion.div 
                                        initial={{ width: 0 }}
                                        animate={{ width: `${p.profile_completeness_pct}%` }}
                                        className={`h-full rounded-full ${p.profile_completeness_pct >= 90 ? 'bg-emerald-500' : p.profile_completeness_pct >= 60 ? 'bg-amber-400' : 'bg-[#c41230]'}`}
                                    />
                                </div>
                            </div>

                            {/* Footer */}
                            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                                <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                                    <Calendar className="w-3.5 h-3.5" />
                                    <span>Updated {new Date(p.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                                </div>
                                <button 
                                    onClick={() => navigate(`/vendor-profile/${p.id}/edit`)}
                                    className="flex items-center gap-1 text-xs font-bold text-[#162f3e] hover:text-[#c41230] transition-colors"
                                >
                                    Manage <ArrowUpRight className="w-3.5 h-3.5" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Insights Side Drawer */}
            <AnimatePresence>
                {isDrawerOpen && selectedProfile && (
                    <>
                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setIsDrawerOpen(false)}
                            className="fixed inset-0 bg-[#162f3e]/40 backdrop-blur-sm z-[60]"
                        />
                        <motion.div 
                            initial={{ x: '100%' }}
                            animate={{ x: 0 }}
                            exit={{ x: '100%' }}
                            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                            className="fixed top-0 right-0 h-full w-full max-w-md bg-white shadow-2xl z-[70] overflow-y-auto"
                        >
                            <div className="p-8">
                                <div className="flex items-center justify-between mb-8">
                                    <div>
                                        <h2 className="text-2xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>Profile Insights</h2>
                                        <p className="text-xs text-slate-500 mt-1 uppercase tracking-widest font-bold">{selectedProfile.vendor_id || 'Draft'}</p>
                                    </div>
                                    <button onClick={() => setIsDrawerOpen(false)} className="w-10 h-10 rounded-xl hover:bg-slate-50 flex items-center justify-center transition-colors">
                                        <X className="w-5 h-5 text-slate-400" />
                                    </button>
                                </div>

                                <div className="p-6 rounded-3xl bg-slate-50 border border-slate-100 mb-8">
                                    <div className="flex items-center gap-4 mb-4">
                                        <div className="w-14 h-14 rounded-2xl bg-white flex items-center justify-center text-2xl font-bold text-[#162f3e] shadow-sm">
                                            {selectedProfile.profile_completeness_pct}%
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>Completeness Score</p>
                                            <p className="text-xs text-slate-500">Based on platform metadata standards</p>
                                        </div>
                                    </div>
                                    <p className="text-xs text-[#475569] leading-relaxed">
                                        A higher score increases your chances of appearing in predictive tender matches by up to 40%.
                                    </p>
                                </div>

                                {/* Checklist */}
                                <div className="space-y-8">
                                    {['Identity', 'Geography', 'Business', 'Financials', 'Certifications', 'Compliance', 'Notifications'].map(section => {
                                        const items = selectedProfile.completeness_details.filter(d => d.section === section);
                                        const filled = items.filter(d => d.is_filled).length;
                                        
                                        return (
                                            <div key={section} className="space-y-3">
                                                <div className="flex items-center justify-between">
                                                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">{section}</h3>
                                                    <span className="text-[10px] font-bold text-[#162f3e] bg-slate-100 px-2 py-0.5 rounded-full">
                                                        {filled}/{items.length}
                                                    </span>
                                                </div>
                                                <div className="space-y-2">
                                                    {items.map(item => (
                                                        <div key={item.label} className="flex items-center justify-between p-3 rounded-xl border border-slate-50 hover:border-slate-100 transition-colors">
                                                            <span className={`text-[13px] font-medium ${item.is_filled ? 'text-[#162f3e]' : 'text-slate-400'}`}>
                                                                {item.label}
                                                            </span>
                                                            {item.is_filled ? (
                                                                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                                                            ) : (
                                                                <div className="w-4 h-4 rounded-full border-2 border-slate-200" />
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>

                                <div className="mt-12">
                                    <button 
                                        onClick={() => navigate(`/vendor-profile/${selectedProfile.id}/edit`)}
                                        className="w-full pm-btn-primary py-4 justify-center"
                                    >
                                        Optimize Profile Now
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
};
