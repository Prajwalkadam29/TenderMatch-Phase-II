import React, { useState, useEffect } from 'react';
import {
    Search, Loader2, AlertCircle, Sparkles,
    Award, Building2, ChevronDown, ChevronUp,
} from 'lucide-react';
import api from '../services/api';
import { vendorProfileService } from '../services/vendorProfileApi';
import type { VendorProfileResponse } from '../types/vendorProfile';

// ─── Score helpers ─────────────────────────────────────────────────────────

const scoreColor = (s: number) => {
    if (s >= 75) return '#16a34a';   // green
    if (s >= 50) return '#d97706';   // amber
    return '#dc2626';                 // red
};
const scoreBg = (s: number) => {
    if (s >= 75) return '#f0fdf4';
    if (s >= 50) return '#fffbeb';
    return '#fef2f2';
};
const scoreLabel = (s: number) => {
    if (s >= 75) return 'Strong Match';
    if (s >= 50) return 'Moderate Match';
    return 'Weak Match';
};

function ScoreRing({ score }: { score: number }) {
    const r = 28;
    const circ = 2 * Math.PI * r;
    const dash = (score / 100) * circ;
    const color = scoreColor(score);
    return (
        <svg width={72} height={72} viewBox="0 0 72 72">
            <circle cx={36} cy={36} r={r} fill="none" stroke="#e2e8f0" strokeWidth={6} />
            <circle
                cx={36} cy={36} r={r} fill="none"
                stroke={color} strokeWidth={6}
                strokeDasharray={`${dash} ${circ}`}
                strokeLinecap="round"
                transform="rotate(-90 36 36)"
                style={{ transition: 'stroke-dasharray 0.6s ease' }}
            />
            <text x={36} y={36} textAnchor="middle" dominantBaseline="central"
                fill={color} fontWeight={700} fontSize={14} fontFamily="Poppins">
                {Math.round(score)}
            </text>
        </svg>
    );
}

function MiniBar({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div>
            <div className="flex justify-between items-center mb-1">
                <span className="text-xs text-slate-500">{label}</span>
                <span className="text-xs font-semibold" style={{ color }}>{(value * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${value * 100}%`, background: color }}
                />
            </div>
        </div>
    );
}

// ─── Match card ────────────────────────────────────────────────────────────

function MatchCard({ result, rank }: { result: any; rank: number }) {
    const [open, setOpen] = useState(false);
    
    const mr = result.match_result;
    const meta = mr._meta;
    const hardFiltersPass = mr.hard_filter_results.overall_pass;
    const finalScore = (mr.weighted_score.final_score || 0) * 100;

    const color = scoreColor(finalScore);
    const bg    = scoreBg(finalScore);

    return (
        <div className="pm-card flex flex-col gap-4" style={{ borderLeft: `4px solid ${hardFiltersPass ? color : '#dc2626'}` }}>
            {/* Header row */}
            <div className="flex items-start gap-4">
                {/* Rank badge */}
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-sm font-bold text-slate-500">
                    #{rank}
                </div>

                {/* Score ring */}
                <ScoreRing score={hardFiltersPass ? finalScore : 0} />

                {/* Main info */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="text-base font-bold text-[#162f3e] truncate" style={{ fontFamily: 'Poppins' }}>
                            Tender: {meta.tender_id}
                        </h3>
                        <span
                            className="text-xs px-2 py-0.5 rounded-full font-semibold"
                            style={{ background: hardFiltersPass ? bg : '#fef2f2', color: hardFiltersPass ? color : '#dc2626' }}
                        >
                            {hardFiltersPass ? scoreLabel(finalScore) : 'Disqualified'}
                        </span>
                    </div>

                    {/* Breakdown bars */}
                    {hardFiltersPass && mr.weighted_score.breakdown && (
                        <div className="grid grid-cols-2 gap-3 mt-2">
                            <MiniBar label="Domain / Semantic" value={mr.weighted_score.breakdown.domain_semantic_similarity?.raw_score || mr.weighted_score.breakdown.domain?.raw_score || 0} color="#162f3e" />
                            <MiniBar label="Financial Capacity" value={mr.weighted_score.breakdown.financial_capacity_ratio?.raw_score || mr.weighted_score.breakdown.financial?.raw_score || 0} color="#c41230" />
                        </div>
                    )}
                    
                    {!hardFiltersPass && (
                         <div className="text-sm text-red-600 mt-2 font-medium">
                            {mr.hard_filter_results.disqualification_reason}
                         </div>
                    )}
                </div>

                {/* Expand toggle */}
                <button
                    onClick={() => setOpen(o => !o)}
                    className="flex-shrink-0 p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 transition-colors"
                >
                    {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
            </div>

            {/* Quick meta */}
            <div className="flex flex-wrap gap-3">
                <span className="flex items-center gap-1 text-xs text-slate-500">
                    <Award className="w-3 h-3 text-[#c41230]" />
                    {mr.recommendation}
                </span>
            </div>

            {/* Expanded detail */}
            {open && (
                <div className="space-y-4 pt-3 border-t border-slate-100">
                    <div>
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Recommendation Detail</p>
                        <p className="text-sm text-[#162f3e] leading-relaxed">{mr.recommendation_detail}</p>
                    </div>

                    {mr.human_readable_explanation && (
                        <div className="p-3 rounded-xl bg-[#162f3e]/5 border border-[#162f3e]/10">
                            <p className="text-xs font-semibold text-[#162f3e] mb-1 flex items-center gap-1">
                                <Sparkles className="w-3 h-3 text-[#c41230]" /> Analysis
                            </p>
                            <p className="text-sm text-slate-600 leading-relaxed">{mr.human_readable_explanation}</p>
                        </div>
                    )}

                    <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                         <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1">
                                Hard Filters Check
                         </p>
                         <ul className="text-xs text-slate-600 space-y-2">
                             {mr.hard_filter_results.filters.map((f: any) => (
                                 <li key={f.filter_id} className="flex gap-2">
                                     <span className={f.result === 'PASS' ? 'text-green-600 font-bold' : 'text-red-600 font-bold'}>
                                         [{f.result}]
                                     </span>
                                     <span>{f.detail}</span>
                                 </li>
                             ))}
                         </ul>
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── Main page ─────────────────────────────────────────────────────────────

export const AIMatching = () => {
    const [vendorId, setVendorId]   = useState('');
    const [loading, setLoading]     = useState(false);
    const [results, setResults]     = useState<any[]>([]);
    const [error, setError]         = useState('');
    const [ran, setRan]             = useState(false);
    
    const [myVendors, setMyVendors] = useState<VendorProfileResponse[]>([]);
    const [vendorsLoading, setVendorsLoading] = useState(true);

    useEffect(() => {
        const init = async () => {
            try {
                const profiles = await vendorProfileService.list();
                setMyVendors(profiles);
                if (profiles.length > 0) {
                    setVendorId(profiles[0].id);
                }
            } catch (err) {
                console.error("Failed to fetch vendor profiles", err);
            } finally {
                setVendorsLoading(false);
            }
        };
        init();
    }, []);

    const run = async () => {
        if (!vendorId.trim()) {
            setError('Please select a valid Vendor Profile.');
            return;
        }
        setLoading(true); setError(''); setRan(false); setResults([]);
        try {
            const { data } = await api.post(`/match/structured/run/${vendorId}`);
            setResults(data.results || []);
            setRan(true);
        } catch (err: unknown) {
            const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Matching failed';
            setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
        }
        setLoading(false);
    };

    return (
        <div style={{ fontFamily: 'DM Sans' }}>
            {/* Header */}
            <div className="mb-8">
                <span className="pm-badge mb-3">Structured Match + AI</span>
                <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                    Tender <span className="text-[#c41230]">Matching</span> Engine
                </h1>
                <p className="text-[#475569]">
                    Strict eligibility filtering followed by field-wise weighted scoring and semantic requirement understanding.
                </p>
            </div>

            {/* Query form */}
            <div className="pm-card mb-8">
                <h2 className="text-base font-bold text-[#162f3e] mb-5" style={{ fontFamily: 'Poppins' }}>
                    Evaluate Vendor
                </h2>
                <div className="grid grid-cols-1 gap-5">
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                            Select Vendor Profile *
                        </label>
                        <div className="relative">
                            <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 z-10" />
                            {vendorsLoading ? (
                                <div className="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-xl text-sm bg-slate-50 flex items-center gap-2 text-slate-500">
                                    <Loader2 className="w-4 h-4 animate-spin" /> Fetching your profiles...
                                </div>
                            ) : myVendors.length > 0 ? (
                                <>
                                    <select
                                        value={vendorId}
                                        onChange={e => setVendorId(e.target.value)}
                                        className="w-full pl-10 pr-10 py-3 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 transition appearance-none relative z-0"
                                    >
                                        {myVendors.map(v => (
                                            <option key={v.id} value={v.id}>
                                                {v.identity.company_legal_name} ({v.vendor_id || v.id.slice(-6)}) - {v.profile_completeness_pct}% Complete
                                            </option>
                                        ))}
                                    </select>
                                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none z-10" />
                                </>
                            ) : (
                                <div className="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-xl text-sm bg-slate-50 text-slate-500">
                                    No vendor profiles found. Create one first!
                                </div>
                            )}
                        </div>
                        <p className="text-xs text-slate-400 mt-1.5">
                            Matching will evaluate the vendor against all available tenders in the database simultaneously.
                        </p>
                    </div>
                </div>

                {error && (
                    <div className="flex items-center gap-2 mt-4 p-3 rounded-xl bg-red-50 border border-red-200">
                        <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                        <p className="text-sm text-red-600">{error}</p>
                    </div>
                )}

                <button
                    onClick={run}
                    disabled={loading || !vendorId.trim() || myVendors.length === 0}
                    className="pm-btn-primary mt-5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading
                        ? <><Loader2 className="w-4 h-4 animate-spin" /> Evaluating DB Tenders...</>
                        : <><Search className="w-4 h-4" /> Run Structured Matching</>}
                </button>
            </div>

            {/* Results */}
            {ran && (
                <div>
                    <div className="flex items-center justify-between mb-5">
                        <h2 className="text-xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>
                            {results.length > 0
                                ? <>{results.length} Match Result{results.length > 1 ? 's' : ''} Evaluated</>
                                : 'No Tenders Evaluated'}
                        </h2>
                        {results.length > 0 && (
                            <p className="text-sm text-slate-500">Sorted by Final Score ↓</p>
                        )}
                    </div>

                    {results.length === 0 ? (
                        <div className="pm-card text-center py-16">
                            <Search className="w-12 h-12 text-slate-200 mx-auto mb-4" />
                            <p className="text-[#162f3e] font-semibold mb-2">No tenders in database yet</p>
                            <p className="text-sm text-slate-400">
                                Please ingest some mock tenders into the MongoDB instance first.
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {results.map((r, i) => (
                                <MatchCard key={r.match_result._meta.match_id} result={r} rank={i + 1} />
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

