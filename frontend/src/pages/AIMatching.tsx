import React, { useState, useMemo } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
    Search, Loader2, AlertCircle, Sparkles,
    Award, Building2, ChevronDown, ChevronUp,
    Filter, Calendar, Target, CheckCircle2,
    XCircle, ArrowRight, Bookmark, BarChart3,
    Clock, Globe, Download
} from 'lucide-react';
import api from '../services/api';
import { vendorProfileService } from '../services/vendorProfileApi';
import type { VendorProfileResponse } from '../types/vendorProfile';
import { motion, AnimatePresence } from 'framer-motion';

// ─── Score helpers ─────────────────────────────────────────────────────────

const getScoreColor = (s: number) => {
    if (s >= 85) return '#16a34a';   // green
    if (s >= 70) return '#0ea5e9';   // blue
    if (s >= 50) return '#f59e0b';   // amber
    return '#dc2626';                 // red
};

const getScoreBg = (s: number) => {
    if (s >= 85) return '#f0fdf4';
    if (s >= 70) return '#f0f9ff';
    if (s >= 50) return '#fffbe6';
    return '#fef2f2';
};

function ScoreRing({ score }: { score: number }) {
    const r = 32;
    const circ = 2 * Math.PI * r;
    const dash = (score / 100) * circ;
    const color = getScoreColor(score);
    return (
        <div className="relative flex items-center justify-center">
            <svg width={80} height={80} viewBox="0 0 80 80">
                <circle cx={40} cy={40} r={r} fill="none" stroke="#f1f5f9" strokeWidth={8} />
                <motion.circle
                    cx={40} cy={40} r={r} fill="none"
                    stroke={color} strokeWidth={8}
                    strokeDasharray={circ}
                    initial={{ strokeDashoffset: circ }}
                    animate={{ strokeDashoffset: circ - dash }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    strokeLinecap="round"
                    transform="rotate(-90 40 40)"
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-black text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>{Math.round(score)}</span>
                <span className="text-[8px] font-bold text-slate-400 uppercase tracking-tighter">%</span>
            </div>
        </div>
    );
}

function StatBar({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div className="space-y-1.5">
            <div className="flex justify-between items-center">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{label}</span>
                <span className="text-[10px] font-black" style={{ color }}>{Math.round(value)}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden border border-slate-200/50">
                <motion.div
                    className="h-full rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${value}%` }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    style={{ background: color }}
                />
            </div>
        </div>
    );
}

// ─── Match card ────────────────────────────────────────────────────────────

function MatchCard({ result, rank }: { result: any; rank: number }) {
    const [open, setOpen] = useState(false);
    
    const score = result.final_score;
    const color = getScoreColor(score);
    const bg = getScoreBg(score);

    return (
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: rank * 0.1 }}
            className="pm-card overflow-hidden border-l-4 relative"
            style={{ borderLeftColor: result.is_eligible ? color : '#cbd5e1' }}
        >
            {!result.is_eligible && (
                <div className="absolute top-0 right-0 px-4 py-1 bg-slate-100 text-slate-500 text-[10px] font-black uppercase rounded-bl-xl tracking-widest">
                    Ineligible
                </div>
            )}

            <div className="flex flex-col lg:flex-row gap-8 items-start">
                {/* Visual Identity */}
                <div className="flex-shrink-0 flex flex-col items-center gap-3">
                    <ScoreRing score={score} />
                    <div className="text-center">
                        <span className="text-[9px] font-black uppercase tracking-widest text-slate-400">Match Grade</span>
                        <div className="text-xs font-bold mt-0.5" style={{ color }}>{result.recommendation}</div>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-[10px] font-black rounded-md">#{rank}</span>
                                <span className="px-2 py-0.5 bg-[#fdf2f2] text-[#c41230] text-[10px] font-black rounded-md uppercase tracking-wider">{result.sector}</span>
                            </div>
                            <h3 className="text-xl font-bold text-[#162f3e] leading-tight" style={{ fontFamily: 'Poppins' }}>
                                {result.tender_title}
                            </h3>
                        </div>
                        <div className="flex flex-shrink-0 gap-2">
                            <button className="p-2.5 rounded-xl border border-slate-200 text-slate-400 hover:text-[#c41230] hover:bg-red-50 transition-all">
                                <Bookmark className="w-4 h-4" />
                            </button>
                            <button className="pm-btn-primary py-2 px-5 text-xs flex items-center gap-2 group">
                                APPLY NOW
                                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                            </button>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6 p-4 bg-slate-50/50 rounded-2xl border border-slate-100">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-white shadow-sm flex items-center justify-center">
                                <Calendar className="w-4 h-4 text-[#c41230]" />
                            </div>
                            <div>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Deadline</p>
                                <p className="text-xs font-bold text-[#162f3e]">{result.deadline ? new Date(result.deadline).toLocaleDateString() : 'N/A'}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-white shadow-sm flex items-center justify-center">
                                <Target className="w-4 h-4 text-[#162f3e]" />
                            </div>
                            <div>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Score Accuracy</p>
                                <p className="text-xs font-bold text-[#162f3e]">{result.score_breakdown.confidence_score}% Confidence</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-white shadow-sm flex items-center justify-center">
                                <Globe className="w-4 h-4 text-sky-600" />
                            </div>
                            <div>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Eligibility</p>
                                <div className="flex items-center gap-1.5">
                                    {result.is_eligible ? (
                                        <><CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> <span className="text-xs font-bold text-emerald-600">Qualified</span></>
                                    ) : (
                                        <><XCircle className="w-3.5 h-3.5 text-red-500" /> <span className="text-xs font-bold text-red-600">Ineligible</span></>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <button 
                                onClick={() => setOpen(!open)}
                                className="text-xs font-black text-[#c41230] hover:underline flex items-center gap-1.5 tracking-widest"
                            >
                                <BarChart3 className="w-3.5 h-3.5" />
                                {open ? 'HIDE ANALYSIS' : 'VIEW SCORE BREAKDOWN'}
                            </button>
                        </div>

                        <AnimatePresence>
                            {open && (
                                <motion.div 
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="overflow-hidden"
                                >
                                    <div className="pt-4 grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6">
                                        <StatBar label="Domain Alignment" value={result.score_breakdown.domain_fit} color="#162f3e" />
                                        <StatBar label="Geographic Reach" value={result.score_breakdown.geography_fit} color="#0ea5e9" />
                                        <StatBar label="Financial Capacity" value={result.score_breakdown.financial_capacity} color="#c41230" />
                                        <StatBar label="Experience Record" value={result.score_breakdown.experience_track_record} color="#8b5cf6" />
                                        <StatBar label="Certs & Compliance" value={result.score_breakdown.certifications_compliance} color="#10b981" />
                                        <StatBar label="Semantic Similarity" value={result.score_breakdown.capability_similarity} color="#f59e0b" />
                                    </div>
                                    
                                    <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-100/50">
                                            <p className="text-[10px] font-black text-emerald-700 uppercase tracking-widest mb-3 flex items-center gap-2">
                                                <CheckCircle2 className="w-3.5 h-3.5" /> Key Strengths
                                            </p>
                                            <ul className="space-y-2">
                                                {result.strengths?.map((s: string, idx: number) => (
                                                    <li key={idx} className="text-xs text-emerald-800 flex items-start gap-2">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1" />
                                                        {s}
                                                    </li>
                                                )) || <li className="text-xs text-slate-400 italic">No specific strengths listed.</li>}
                                            </ul>
                                        </div>
                                        <div className="p-4 rounded-2xl bg-red-50 border border-red-100/50">
                                            <p className="text-[10px] font-black text-red-700 uppercase tracking-widest mb-3 flex items-center gap-2">
                                                <AlertCircle className="w-3.5 h-3.5" /> Weaknesses
                                            </p>
                                            <ul className="space-y-2">
                                                {result.weaknesses?.map((w: string, idx: number) => (
                                                    <li key={idx} className="text-xs text-red-800 flex items-start gap-2">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1" />
                                                        {w}
                                                    </li>
                                                )) || <li className="text-xs text-slate-400 italic">No specific weaknesses identified.</li>}
                                                {!result.is_eligible && result.disqualification_reasons?.map((dr: string, idx: number) => (
                                                    <li key={`dr-${idx}`} className="text-xs font-bold text-red-900 flex items-start gap-2">
                                                        <XCircle className="w-3 h-3 mt-0.5" />
                                                        {dr}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>

                                    <div className="mt-4 p-4 rounded-2xl bg-[#162f3e] text-white border border-[#162f3e]">
                                        <p className="text-[10px] font-black uppercase tracking-widest opacity-60 mb-2 flex items-center gap-2">
                                            <Sparkles className="w-3.5 h-3.5" /> AI Executive Summary
                                        </p>
                                        <p className="text-sm leading-relaxed font-medium">
                                            {result.explanation_text || result.explanation}
                                        </p>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </motion.div>
    );
}

// ─── Main page ─────────────────────────────────────────────────────────────

export const AIMatching = () => {
    const [vendorProfileId, setVendorProfileId] = useState('');
    const [ran, setRan] = useState(false);
    
    // Filters
    const [filterSector, setFilterSector] = useState('All');
    const [filterMinScore, setFilterMinScore] = useState(0);
    const [filterEligibleOnly, setFilterEligibleOnly] = useState(false);

    // 1. Fetch vendor profiles using TanStack Query
    const { data: myVendors = [], isLoading: vendorsLoading } = useQuery({
        queryKey: ['vendorProfiles'],
        queryFn: async () => {
            const profiles = await vendorProfileService.list();
            if (profiles.length > 0 && !vendorProfileId) {
                setVendorProfileId(profiles[0].id);
            }
            return profiles;
        },
    });

    // 2. Mutation for running the match cycle
    const matchMutation = useMutation({
        mutationFn: async (id: string) => {
            const { data } = await api.post(`/match/run`, { vendor_profile_id: id });
            return data || [];
        },
        onSuccess: () => {
            setRan(true);
        }
    });

    const run = () => {
        if (!vendorProfileId.trim()) return;
        setRan(false);
        matchMutation.mutate(vendorProfileId);
    };

    const results = matchMutation.data || [];
    const loading = matchMutation.isPending;
    
    // Process error message
    let errorMsg = '';
    if (matchMutation.isError) {
        const err = matchMutation.error as any;
        errorMsg = err?.response?.data?.detail ?? 'Matching cycle failed';
        if (typeof errorMsg !== 'string') errorMsg = JSON.stringify(errorMsg);
    }
    if (!vendorProfileId.trim() && matchMutation.isIdle && ran) {
        // Just as a fallback if they try to run without id (though button is disabled)
        errorMsg = 'Please select a valid Vendor Profile.';
    }

    const exportCsv = () => {
        if (!filteredResults.length) return;
        const headers = ['Tender Title', 'Sector', 'Final Score', 'Recommendation', 'Eligible', 'Created At'];
        const rows = filteredResults.map(r => [
            `"${r.tender_title}"`,
            r.sector,
            `${r.final_score}%`,
            r.recommendation,
            r.is_eligible ? 'Yes' : 'No',
            new Date(r.created_at).toLocaleDateString()
        ]);
        
        const csvContent = "data:text/csv;charset=utf-8," 
            + headers.join(",") + "\n" 
            + rows.map(e => e.join(",")).join("\n");
            
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `TenderMatch_Report_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const sectors = useMemo(() => {
        const s = new Set(results.map(r => r.sector));
        return ['All', ...Array.from(s)];
    }, [results]);

    const filteredResults = useMemo(() => {
        return results.filter(r => {
            if (filterSector !== 'All' && r.sector !== filterSector) return false;
            if (r.final_score < filterMinScore) return false;
            if (filterEligibleOnly && !r.is_eligible) return false;
            return true;
        });
    }, [results, filterSector, filterMinScore, filterEligibleOnly]);

    return (
        <div className="max-w-6xl" style={{ fontFamily: 'DM Sans' }}>
            {/* Header */}
            <div className="mb-10">
                <span className="pm-badge mb-3">Mock AI Matching Engine v4.0</span>
                <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                    Match <span className="text-[#c41230]">Intelligence</span>
                </h1>
                <p className="text-[#475569] text-lg max-w-2xl">
                    High-fidelity procurement matching combining deterministic hard filters with weighted semantic scoring for transparent, explainable results.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Control Panel */}
                <div className="lg:col-span-1 space-y-6">
                    <div className="pm-card sticky top-8">
                        <h2 className="text-sm font-black text-[#162f3e] uppercase tracking-widest mb-6 flex items-center gap-2">
                            <Target className="w-4 h-4 text-[#c41230]" /> Engine Controls
                        </h2>
                        
                        <div className="space-y-6">
                            <div>
                                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2.5 px-1">Vendor Identity</label>
                                <div className="relative">
                                    <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                                    {vendorsLoading ? (
                                        <div className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-xs flex items-center gap-2 text-slate-500">
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Fetching...
                                        </div>
                                    ) : (
                                        <select
                                            value={vendorProfileId}
                                            onChange={e => setVendorProfileId(e.target.value)}
                                            className="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-2xl text-xs font-bold text-[#162f3e] focus:outline-none focus:border-[#c41230] transition appearance-none"
                                        >
                                            {myVendors.map(v => (
                                                <option key={v.id} value={v.id}>{v.identity.company_legal_name}</option>
                                            ))}
                                        </select>
                                    )}
                                </div>
                            </div>

                            <button
                                onClick={run}
                                disabled={loading || !vendorProfileId || myVendors.length === 0}
                                className="w-full pm-btn-primary py-3.5 flex items-center justify-center gap-2 shadow-xl shadow-[#c41230]/20 disabled:opacity-50"
                            >
                                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                                RUN MATCH CYCLE
                            </button>

                            {ran && filteredResults.length > 0 && (
                                <button
                                    onClick={exportCsv}
                                    className="w-full py-3 border-2 border-slate-200 rounded-2xl text-[10px] font-black text-[#162f3e] uppercase tracking-widest hover:bg-slate-50 transition flex items-center justify-center gap-2"
                                >
                                    <Download className="w-3.5 h-3.5 text-[#c41230]" /> Download Match Report (CSV)
                                </button>
                            )}

                            {errorMsg && (
                                <div className="p-3 rounded-xl bg-red-50 border border-red-100 flex items-start gap-2">
                                    <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                                    <p className="text-[10px] font-bold text-red-700 leading-tight">{errorMsg}</p>
                                </div>
                            )}
                        </div>

                        {ran && (
                            <div className="mt-10 pt-8 border-t border-slate-100 space-y-6">
                                <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-1 flex items-center gap-2">
                                    <Filter className="w-3.5 h-3.5" /> Result Filters
                                </h3>
                                
                                <div>
                                    <label className="block text-[10px] font-bold text-[#162f3e] mb-2 px-1">Industry Sector</label>
                                    <select 
                                        value={filterSector}
                                        onChange={e => setFilterSector(e.target.value)}
                                        className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-[11px] font-bold text-[#162f3e] focus:outline-none focus:border-[#c41230]"
                                    >
                                        {sectors.map(s => <option key={s} value={s}>{s}</option>)}
                                    </select>
                                </div>

                                <div>
                                    <div className="flex justify-between items-center mb-2 px-1">
                                        <label className="block text-[10px] font-bold text-[#162f3e]">Min Score</label>
                                        <span className="text-[10px] font-black text-[#c41230]">{filterMinScore}%</span>
                                    </div>
                                    <input 
                                        type="range" min="0" max="90" step="5"
                                        value={filterMinScore}
                                        onChange={e => setFilterMinScore(parseInt(e.target.value))}
                                        className="w-full accent-[#c41230]"
                                    />
                                </div>

                                <label className="flex items-center gap-3 px-1 cursor-pointer group">
                                    <div className={`w-10 h-5 rounded-full transition-colors relative ${filterEligibleOnly ? 'bg-emerald-500' : 'bg-slate-200'}`}>
                                        <input 
                                            type="checkbox" 
                                            className="sr-only"
                                            checked={filterEligibleOnly}
                                            onChange={e => setFilterEligibleOnly(e.target.checked)}
                                        />
                                        <div className={`absolute top-1 left-1 w-3 h-3 rounded-full bg-white transition-transform ${filterEligibleOnly ? 'translate-x-5' : ''}`} />
                                    </div>
                                    <span className="text-[10px] font-bold text-[#162f3e] group-hover:text-[#c41230] transition-colors">Eligible Only</span>
                                </label>
                            </div>
                        )}
                    </div>
                </div>

                {/* Results List */}
                <div className="lg:col-span-3 space-y-6">
                    {!ran && !loading && (
                        <div className="pm-card py-24 text-center border-dashed border-2 bg-slate-50/30">
                            <div className="w-20 h-20 rounded-3xl bg-white shadow-xl shadow-slate-200/50 flex items-center justify-center mx-auto mb-6">
                                <Sparkles className="w-10 h-10 text-[#c41230]" />
                            </div>
                            <h3 className="text-xl font-bold text-[#162f3e] mb-2" style={{ fontFamily: 'Poppins' }}>Ready to analyze?</h3>
                            <p className="text-slate-500 max-w-sm mx-auto mb-8 text-sm">
                                Select a vendor profile on the left and run the match cycle to identify global procurement opportunities.
                            </p>
                            <div className="flex flex-wrap items-center justify-center gap-6 opacity-40 grayscale">
                                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#162f3e]" /> <span className="text-[10px] font-bold">Semantic</span></div>
                                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#c41230]" /> <span className="text-[10px] font-bold">Financial</span></div>
                                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-sky-500" /> <span className="text-[10px] font-bold">Compliance</span></div>
                            </div>
                        </div>
                    )}

                    {loading && (
                        <div className="space-y-6">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="pm-card animate-pulse">
                                    <div className="flex gap-6">
                                        <div className="w-16 h-16 rounded-2xl bg-slate-100" />
                                        <div className="flex-1 space-y-3">
                                            <div className="h-4 bg-slate-100 rounded w-1/3" />
                                            <div className="h-6 bg-slate-100 rounded w-1/2" />
                                            <div className="grid grid-cols-3 gap-4">
                                                <div className="h-8 bg-slate-50 rounded" />
                                                <div className="h-8 bg-slate-50 rounded" />
                                                <div className="h-8 bg-slate-50 rounded" />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {ran && (
                        <div className="space-y-6">
                            <div className="flex items-center justify-between px-2">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-xl bg-[#c41230]/10 flex items-center justify-center">
                                        <Target className="w-5 h-5 text-[#c41230]" />
                                    </div>
                                    <div>
                                        <h2 className="text-lg font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>
                                            {filteredResults.length} Result{filteredResults.length !== 1 ? 's' : ''} Found
                                        </h2>
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Optimized Ranking Active</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4 text-xs font-bold text-slate-400">
                                    <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> Recent Runs</span>
                                    <span className="text-slate-200">|</span>
                                    <span className="text-[#162f3e] hover:text-[#c41230] cursor-pointer">Export CSV</span>
                                </div>
                            </div>

                            {filteredResults.length === 0 ? (
                                <div className="pm-card text-center py-20">
                                    <Filter className="w-12 h-12 text-slate-200 mx-auto mb-4" />
                                    <h4 className="text-[#162f3e] font-bold mb-1">No matches meet your criteria</h4>
                                    <p className="text-xs text-slate-400">Try adjusting your score or sector filters.</p>
                                </div>
                            ) : (
                                filteredResults.map((r, i) => (
                                    <MatchCard key={r.tender_id} result={r} rank={i + 1} />
                                ))
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
