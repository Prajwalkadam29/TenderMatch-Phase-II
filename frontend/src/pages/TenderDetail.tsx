import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { 
    ArrowLeft, Calendar, MapPin, Building2, 
    FileText, CheckCircle2, XCircle, Info, 
    ChevronRight, ExternalLink, Download, 
    MessageSquare, ShieldCheck, Sparkles,
    BarChart3, Loader2, Share2, Star
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getDocument, getMatchDetail } from '../services/documentService';
import { vendorProfileService } from '../services/vendorProfileApi';
import type { UploadedDocument, MatchResult } from '../types/document';
import type { VendorProfileResponse } from '../types/vendorProfile';

export const TenderDetail: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [selectedProfileId, setSelectedProfileId] = useState<string>('');

    const { data: baseData, isLoading: baseLoading, error: baseError } = useQuery({
        queryKey: ['tenderDetailBase', id],
        queryFn: async () => {
            if (!id) throw new Error('No ID');
            const [tenderData, profileData] = await Promise.all([
                getDocument(id),
                vendorProfileService.list()
            ]);
            return { tenderData, profileData };
        },
        enabled: !!id,
    });

    // Auto-select first profile when data loads
    React.useEffect(() => {
        if (baseData?.profileData?.length && !selectedProfileId) {
            setSelectedProfileId(baseData.profileData[0].id);
        }
    }, [baseData?.profileData]);

    const { data: match, isLoading: matchLoading } = useQuery({
        queryKey: ['tenderMatch', id, selectedProfileId],
        queryFn: async () => {
            if (!id || !selectedProfileId || selectedProfileId === 'none') return null;
            const { getMyDocuments } = await import('../services/documentService');
            const myDocs = await getMyDocuments('vendor');
            if (myDocs.length > 0) {
                return await getMatchDetail(myDocs[0].id, id);
            }
            return null;
        },
        enabled: !!id && !!selectedProfileId && selectedProfileId !== 'none',
    });

    const loading = baseLoading;
    const error = baseError ? 'Failed to load tender details.' : '';
    const tender = baseData?.tenderData;
    const profiles = baseData?.profileData || [];

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-40 text-slate-400">
                <Loader2 className="w-12 h-12 animate-spin mb-4 text-[#c41230]" />
                <p className="text-lg font-medium">Synthesizing tender intelligence...</p>
            </div>
        );
    }

    if (error || !tender) {
        return (
            <div className="pm-card text-center py-20">
                <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                <h2 className="text-xl font-bold text-[#162f3e] mb-2">{error || 'Tender Not Found'}</h2>
                <button onClick={() => navigate('/tenders')} className="pm-btn-secondary py-2 px-6">Back to Tenders</button>
            </div>
        );
    }

    const structuredData = tender.structured_data;
    const stats = match?.match_result?.weighted_score?.breakdown || {};

    return (
        <div className="pb-20" style={{ fontFamily: 'DM Sans' }}>
            {/* Navigation Header */}
            <div className="flex items-center justify-between mb-8">
                <button 
                    onClick={() => navigate('/tenders')}
                    className="flex items-center gap-2 text-slate-500 hover:text-[#c41230] transition-colors font-bold text-xs uppercase tracking-widest"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Results
                </button>
                <div className="flex gap-3">
                    <button className="p-3 rounded-xl bg-white border border-slate-200 text-slate-400 hover:text-[#c41230] hover:border-[#c41230]/20 transition-all">
                        <Share2 className="w-4 h-4" />
                    </button>
                    <button className="p-3 rounded-xl bg-white border border-slate-200 text-slate-400 hover:text-amber-500 hover:border-amber-200 transition-all">
                        <Star className="w-4 h-4" />
                    </button>
                    <button className="pm-btn-primary py-3 px-8 flex items-center gap-2 shadow-lg shadow-[#c41230]/10">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>I'm Interested</span>
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Main Content (Left + Middle) */}
                <div className="xl:col-span-2 space-y-8">
                    {/* Tender Summary Card */}
                    <div className="pm-card !p-8 border-l-4 border-l-[#c41230]">
                        <div className="flex flex-wrap items-start justify-between gap-6 mb-6">
                            <div className="flex-1 min-w-[300px]">
                                <span className="text-[10px] font-black text-[#c41230] uppercase tracking-[0.2em] mb-2 block">Opportunity Overview</span>
                                <h1 className="text-3xl font-bold text-[#162f3e] leading-tight" style={{ fontFamily: 'Poppins' }}>
                                    {tender.original_filename.split('_').slice(1).join('_') || tender.original_filename}
                                </h1>
                                <div className="flex flex-wrap items-center gap-6 mt-4">
                                    <div className="flex items-center gap-2 text-sm text-[#475569]">
                                        <Building2 className="w-4 h-4 text-slate-400" />
                                        <span className="font-medium">{(structuredData as any)?.organization || 'Government/Enterprise Entity'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-sm text-[#475569]">
                                        <MapPin className="w-4 h-4 text-slate-400" />
                                        <span className="font-medium">{structuredData.location || 'Pan-India'}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-sm text-[#475569]">
                                        <Calendar className="w-4 h-4 text-slate-400" />
                                        <span className="font-medium">Deadline: {new Date((structuredData as any)?.deadline || tender.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Status</div>
                                <span className="px-4 py-1.5 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-600 text-xs font-bold uppercase tracking-wider">
                                    Active / Open
                                </span>
                            </div>
                        </div>

                        <div className="h-px bg-slate-100 w-full mb-6" />

                        <div className="space-y-6">
                            <div>
                                <h3 className="text-sm font-bold text-[#162f3e] mb-2 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Scope of Work</h3>
                                <p className="text-[#475569] text-sm leading-relaxed">{structuredData.scope || 'Description not extracted.'}</p>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div>
                                    <h3 className="text-sm font-bold text-[#162f3e] mb-3 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Technical Requirements</h3>
                                    <div className="space-y-2">
                                        {((structuredData as any)?.technical_specs_list || ['Standard operating compliance', 'Quality assurance standards']).map((spec: string, i: number) => (
                                            <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100/50">
                                                <div className="w-1.5 h-1.5 rounded-full bg-[#c41230] mt-1.5 flex-shrink-0" />
                                                <span className="text-xs text-[#475569] leading-snug">{spec}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-[#162f3e] mb-3 uppercase tracking-wide" style={{ fontFamily: 'Poppins' }}>Required Certifications</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {structuredData.certifications.length > 0 ? (
                                            structuredData.certifications.map(cert => (
                                                <span key={cert} className="px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-100 text-blue-600 text-[10px] font-bold uppercase tracking-tight flex items-center gap-2">
                                                    <ShieldCheck className="w-3.5 h-3.5" />
                                                    {cert}
                                                </span>
                                            ))
                                        ) : (
                                            <span className="text-xs text-slate-400 italic">None specifically mentioned.</span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* AI Analysis Section */}
                    <div className="space-y-6">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <Sparkles className="w-5 h-5 text-amber-500" />
                                <h2 className="text-xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>AI Match Analysis</h2>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Compare with:</span>
                                <select 
                                    value={selectedProfileId}
                                    onChange={(e) => setSelectedProfileId(e.target.value)}
                                    className="bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-bold text-[#162f3e] focus:outline-none focus:border-[#c41230]"
                                >
                                    {profiles.map(p => (
                                        <option key={p.id} value={p.id}>{p.identity.company_legal_name}</option>
                                    ))}
                                    <option value="none">No Comparison</option>
                                </select>
                            </div>
                        </div>

                        {matchLoading ? (
                            <div className="pm-card h-64 flex flex-col items-center justify-center text-slate-400">
                                <Loader2 className="w-8 h-8 animate-spin mb-3 text-[#c41230]" />
                                <p className="text-xs font-medium uppercase tracking-widest">Running Weighted Evaluation...</p>
                            </div>
                        ) : match ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Score Breakdown */}
                                <div className="pm-card !p-6 flex flex-col justify-between">
                                    <div>
                                        <div className="flex items-center justify-between mb-6">
                                            <h3 className="text-xs font-black text-slate-400 uppercase tracking-[0.15em]">Weighted Metrics</h3>
                                            <span className="text-2xl font-bold text-[#162f3e]">{Math.round(match.final_score)}%</span>
                                        </div>
                                        <div className="space-y-4">
                                            {Object.entries(stats).map(([key, data]: [string, any]) => (
                                                <div key={key}>
                                                    <div className="flex justify-between text-[11px] mb-1.5">
                                                        <span className="font-bold text-[#475569] uppercase tracking-tighter">
                                                            {key.replace(/_/g, ' ')}
                                                        </span>
                                                        <span className="font-black text-[#162f3e]">{Math.round(data.raw_score * 100)}%</span>
                                                    </div>
                                                    <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                                        <motion.div 
                                                            initial={{ width: 0 }}
                                                            animate={{ width: `${data.raw_score * 100}%` }}
                                                            className="h-full bg-[#162f3e]" 
                                                        />
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="mt-8 pt-4 border-t border-slate-100 flex items-center gap-3">
                                        <div className={`w-3 h-3 rounded-full ${match.eligible ? 'bg-emerald-500' : 'bg-red-500'}`} />
                                        <span className="text-[11px] font-bold text-[#162f3e] uppercase tracking-widest">
                                            {match.eligible ? 'Strict Eligibility Passed' : 'Potential Disqualification'}
                                        </span>
                                    </div>
                                </div>

                                {/* Explanation Card */}
                                <div className="pm-card !p-6 bg-[#162f3e] text-white flex flex-col justify-between overflow-hidden relative">
                                    <div className="absolute top-0 right-0 p-8 opacity-5">
                                        <BrainCircuit className="w-32 h-32" />
                                    </div>
                                    <div className="relative z-10">
                                        <div className="flex items-center gap-2 mb-4">
                                            <MessageSquare className="w-4 h-4 text-[#c41230]" />
                                            <h3 className="text-[10px] font-bold text-[#c41230] uppercase tracking-[0.2em]">LLM Analysis</h3>
                                        </div>
                                        <p className="text-sm font-medium leading-relaxed opacity-90">
                                            {match.explanation || "Analysis pending..."}
                                        </p>
                                    </div>
                                    <div className="relative z-10 mt-6 p-4 rounded-2xl bg-white/5 border border-white/10">
                                        <div className="text-[10px] font-bold text-white/40 uppercase mb-2">Strategy Tip</div>
                                        <p className="text-[11px] text-white/70 italic">
                                            Highlight your {(structuredData as any)?.keywords?.slice(0, 2).join(' & ') || 'core domains'} in the technical response to maximize your competitive edge.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="pm-card py-16 text-center">
                                <Info className="w-10 h-10 text-slate-300 mx-auto mb-4" />
                                <h3 className="text-lg font-bold text-[#162f3e]">No Profile Comparison</h3>
                                <p className="text-sm text-slate-500 mt-2">Select a business profile above to run the predictive match engine.</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Sidebar (Right) */}
                <div className="space-y-8">
                    {/* Action Cards */}
                    <div className="pm-card space-y-4">
                        <h3 className="text-xs font-black text-[#162f3e] uppercase tracking-widest mb-2 px-1">Engagement</h3>
                        <button className="w-full flex items-center justify-between p-4 rounded-2xl bg-slate-50 border border-slate-100 hover:border-[#c41230]/20 hover:bg-red-50/30 transition-all group">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center text-slate-400 group-hover:text-[#c41230]">
                                    <Download className="w-4 h-4" />
                                </div>
                                <span className="text-xs font-bold text-[#162f3e]">Download Original PDF</span>
                            </div>
                            <ChevronRight className="w-4 h-4 text-slate-300" />
                        </button>
                        <button className="w-full flex items-center justify-between p-4 rounded-2xl bg-slate-50 border border-slate-100 hover:border-[#162f3e]/20 transition-all group">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center text-slate-400">
                                    <ExternalLink className="w-4 h-4" />
                                </div>
                                <span className="text-xs font-bold text-[#162f3e]">View Official Portal</span>
                            </div>
                            <ChevronRight className="w-4 h-4 text-slate-300" />
                        </button>
                    </div>

                    {/* Timeline Card */}
                    <div className="pm-card !p-6">
                        <div className="flex items-center gap-2 mb-6 text-[#162f3e]">
                            <BarChart3 className="w-4 h-4" />
                            <h3 className="text-xs font-bold uppercase tracking-widest">Critical Timeline</h3>
                        </div>
                        <div className="space-y-6 relative">
                            <div className="absolute left-1.5 top-2 bottom-2 w-0.5 bg-slate-100" />
                            {[
                                { date: new Date(tender.created_at).toLocaleDateString(), label: 'Published Date', status: 'completed' },
                                { date: 'Within 7 days', label: 'Clarification Deadline', status: 'active' },
                                { date: new Date((structuredData as any)?.deadline || tender.created_at).toLocaleDateString(), label: 'Final Submission', status: 'pending' },
                            ].map((step, i) => (
                                <div key={i} className="flex items-start gap-4 relative z-10">
                                    <div className={`w-3 h-3 rounded-full mt-1.5 ${step.status === 'completed' ? 'bg-[#c41230]' : step.status === 'active' ? 'bg-[#c41230] animate-pulse' : 'bg-slate-200'}`} />
                                    <div>
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">{step.label}</p>
                                        <p className="text-xs font-bold text-[#162f3e]">{step.date}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Keywords Tag Cloud */}
                    <div className="pm-card !p-6">
                        <div className="flex items-center gap-2 mb-4 text-[#162f3e]">
                            <FileText className="w-4 h-4" />
                            <h3 className="text-xs font-bold uppercase tracking-widest">Semantic Key-points</h3>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {tender.keywords.map(kw => (
                                <span key={kw} className="px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-100 text-[10px] font-bold text-[#475569] uppercase tracking-tighter">
                                    #{kw}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
