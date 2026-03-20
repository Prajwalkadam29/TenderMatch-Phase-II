import React, { useState, useEffect } from 'react';
import {
    Search, Loader2, AlertCircle, Sparkles,
    MapPin, Award, Tag, TrendingUp, FileText, ChevronDown, ChevronUp,
} from 'lucide-react';
import { matchVendor, getIndexStatus, getMyDocuments } from '../services/documentService';
import type { MatchResult, IndexStatus, UploadedDocument } from '../types/document';

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

function MatchCard({ result, rank }: { result: MatchResult; rank: number }) {
    const [open, setOpen] = useState(false);
    const color = scoreColor(result.final_score);
    const bg    = scoreBg(result.final_score);

    return (
        <div className="pm-card flex flex-col gap-4" style={{ borderLeft: `4px solid ${color}` }}>
            {/* Header row */}
            <div className="flex items-start gap-4">
                {/* Rank badge */}
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-sm font-bold text-slate-500">
                    #{rank}
                </div>

                {/* Score ring */}
                <ScoreRing score={result.final_score} />

                {/* Main info */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="text-base font-bold text-[#162f3e] truncate" style={{ fontFamily: 'Poppins' }}>
                            {result.tender_filename || result.tender_id}
                        </h3>
                        <span
                            className="text-xs px-2 py-0.5 rounded-full font-semibold"
                            style={{ background: bg, color }}
                        >
                            {scoreLabel(result.final_score)}
                        </span>
                    </div>

                    {/* Score bars */}
                    <div className="grid grid-cols-2 gap-3 mt-2">
                        <MiniBar label="Semantic Doc" value={result.semantic_score} color="#162f3e" />
                        <MiniBar label="Keyword Match" value={result.keyword_score} color="#c41230" />
                    </div>
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
                {result.tender_summary?.location && (
                    <span className="flex items-center gap-1 text-xs text-slate-500">
                        <MapPin className="w-3 h-3 text-[#c41230]" />
                        {result.tender_summary.location}
                    </span>
                )}
                {result.tender_summary?.certifications?.length > 0 && (
                    <span className="flex items-center gap-1 text-xs text-slate-500">
                        <Award className="w-3 h-3 text-[#c41230]" />
                        {result.tender_summary.certifications.slice(0, 2).join(', ')}
                    </span>
                )}
            </div>

            {/* Expanded detail */}
            {open && (
                <div className="space-y-4 pt-3 border-t border-slate-100">
                    {result.tender_summary?.scope && (
                        <div>
                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Scope</p>
                            <p className="text-sm text-[#162f3e] leading-relaxed">{result.tender_summary.scope}</p>
                        </div>
                    )}

                    {result.tender_keywords?.length > 0 && (
                        <div>
                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1">
                                <Tag className="w-3 h-3" /> Matched Keywords
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                                {result.tender_keywords.map(k => (
                                    <span key={k} className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{k}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {result.explanation && (
                        <div className="p-3 rounded-xl bg-[#162f3e]/5 border border-[#162f3e]/10">
                            <p className="text-xs font-semibold text-[#162f3e] mb-1 flex items-center gap-1">
                                <Sparkles className="w-3 h-3 text-[#c41230]" /> AI Analysis
                            </p>
                            <p className="text-sm text-slate-600 leading-relaxed">{result.explanation}</p>
                        </div>
                    )}

                    <p className="text-xs text-slate-400 font-mono">Tender ID: {result.tender_id}</p>
                </div>
            )}
        </div>
    );
}


// ─── Main page ─────────────────────────────────────────────────────────────

export const AIMatching = () => {
    const [vendorId, setVendorId]   = useState('');
    const [k, setK]                 = useState(10);
    const [explain, setExplain]     = useState(false);
    const [loading, setLoading]     = useState(false);
    const [results, setResults]     = useState<MatchResult[]>([]);
    const [error, setError]         = useState('');
    const [ran, setRan]             = useState(false);
    const [status, setStatus]       = useState<IndexStatus | null>(null);
    const [statusLoading, setStatusLoading] = useState(false);
    const [myVendors, setMyVendors] = useState<UploadedDocument[]>([]);
    const [vendorsLoading, setVendorsLoading] = useState(true);

    const fetchStatus = async () => {
        setStatusLoading(true);
        try { setStatus(await getIndexStatus()); } catch { /* ignore */ }
        setStatusLoading(false);
    };

    useEffect(() => {
        const init = async () => {
            fetchStatus();
            try {
                const docs = await getMyDocuments('vendor');
                setMyVendors(docs);
                if (docs.length > 0) {
                    setVendorId(docs[0].id);
                }
            } catch (err) {
                console.error("Failed to fetch vendors", err);
            } finally {
                setVendorsLoading(false);
            }
        };
        init();
    }, []);

    const run = async () => {
        if (!vendorId.trim() || vendorId.length !== 24) {
            setError('Please enter a valid 24-character MongoDB vendor ID.');
            return;
        }
        setLoading(true); setError(''); setRan(false); setResults([]);
        try {
            const resp = await matchVendor(vendorId.trim(), k, explain);
            setResults(resp.results);
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
                <span className="pm-badge mb-3">FAISS + Sentence Transformers</span>
                <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                    AI <span className="text-[#c41230]">Matching</span> Engine
                </h1>
                <p className="text-[#475569]">
                    Semantic document similarity + keyword embedding matching. Scores scaled 0–100.
                </p>
            </div>

            {/* Index status bar */}
            <div className="pm-card mb-8 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-6 flex-wrap">
                    <Stat label="FAISS Vectors" value={status?.faiss_index_size ?? '—'} />
                    <Stat label="Total Docs" value={status?.total_documents ?? '—'} />
                    <Stat label="Vendors" value={status?.total_vendors ?? '—'} color="#162f3e" />
                    <Stat label="Tenders" value={status?.total_tenders ?? '—'} color="#c41230" />
                </div>
                <button
                    onClick={fetchStatus}
                    disabled={statusLoading}
                    className="pm-btn-secondary text-sm flex items-center gap-2"
                >
                    {statusLoading
                        ? <Loader2 className="w-3 h-3 animate-spin" />
                        : <TrendingUp className="w-3 h-3" />}
                    Refresh Status
                </button>
            </div>

            {/* Query form */}
            <div className="pm-card mb-8">
                <h2 className="text-base font-bold text-[#162f3e] mb-5" style={{ fontFamily: 'Poppins' }}>
                    Configure Match Query
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <div className="md:col-span-2">
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                            Select Vendor Profile *
                        </label>
                        <div className="relative">
                            <FileText className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 z-10" />
                            {vendorsLoading ? (
                                <div className="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-xl text-sm bg-slate-50 flex items-center gap-2 text-slate-500">
                                    <Loader2 className="w-4 h-4 animate-spin" /> Loading your profiles...
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
                                                {v.original_filename} ({v.id.slice(-6)})
                                            </option>
                                        ))}
                                    </select>
                                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none z-10" />
                                </>
                            ) : (
                                <div className="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-xl text-sm bg-slate-50 text-slate-500">
                                    No vendor profiles found. Upload one first.
                                </div>
                            )}
                        </div>
                        <p className="text-xs text-slate-400 mt-1.5">
                            Showing documents uploaded by your account.
                        </p>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                            Top K Results
                        </label>
                        <select
                            value={k}
                            onChange={e => setK(Number(e.target.value))}
                            className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm
                                       focus:outline-none focus:border-[#c41230] transition bg-white"
                        >
                            {[3, 5, 10, 20, 50].map(n => (
                                <option key={n} value={n}>Top {n}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Explain toggle */}
                <div className="flex items-center gap-3 mt-5 pt-5 border-t border-slate-100">
                    <button
                        onClick={() => setExplain(v => !v)}
                        className={`relative w-11 h-6 rounded-full transition-colors duration-200 focus:outline-none ${explain ? 'bg-[#c41230]' : 'bg-slate-200'}`}
                        role="switch"
                        aria-checked={explain}
                    >
                        <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200 ${explain ? 'translate-x-5' : ''}`} />
                    </button>
                    <div>
                        <p className="text-sm font-medium text-[#162f3e]">
                            <Sparkles className="w-4 h-4 inline mr-1 text-[#c41230]" />
                            Groq AI Explanation
                        </p>
                        <p className="text-xs text-slate-400">Adds ~5 seconds. Explains why each match is high or low.</p>
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
                    disabled={loading || !vendorId.trim()}
                    className="pm-btn-primary mt-5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading
                        ? <><Loader2 className="w-4 h-4 animate-spin" /> Finding Matches…</>
                        : <><Search className="w-4 h-4" /> Find Matching Tenders</>}
                </button>
            </div>

            {/* Results */}
            {ran && (
                <div>
                    <div className="flex items-center justify-between mb-5">
                        <h2 className="text-xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>
                            {results.length > 0
                                ? <>{results.length} Tender{results.length > 1 ? 's' : ''} Found</>
                                : 'No Matches Found'}
                        </h2>
                        {results.length > 0 && (
                            <p className="text-sm text-slate-500">Sorted by Final Score ↓</p>
                        )}
                    </div>

                    {results.length === 0 ? (
                        <div className="pm-card text-center py-16">
                            <Search className="w-12 h-12 text-slate-200 mx-auto mb-4" />
                            <p className="text-[#162f3e] font-semibold mb-2">No tenders indexed yet</p>
                            <p className="text-sm text-slate-400">
                                Go to <strong>Document Upload</strong> and upload at least one tender document first.
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {results.map((r, i) => (
                                <MatchCard key={r.tender_id} result={r} rank={i + 1} />
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

const Stat = ({ label, value, color }: { label: string; value: string | number; color?: string }) => (
    <div>
        <p className="text-2xl font-bold" style={{ fontFamily: 'Poppins', color: color ?? '#162f3e' }}>{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
    </div>
);
