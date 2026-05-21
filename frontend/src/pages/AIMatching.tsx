import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Search, Loader2, AlertCircle, Sparkles, CheckCircle2, XCircle,
    ChevronDown, ChevronUp, BarChart3, ArrowRight, Zap, Brain,
    ThumbsUp, ThumbsDown, Send, Trophy, Flag, Clock, Target
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { vendorProfileService } from '../services/vendorProfileApi';
import {
    matchingService,
    type MatchDetailFull,
    type TaskState,
} from '../services/matchingService';

// ─── Score helpers ──────────────────────────────────────────────────────────

const getScoreColor = (s: number) => s >= 80 ? '#16a34a' : s >= 65 ? '#0ea5e9' : s >= 45 ? '#f59e0b' : '#dc2626';
const getScoreBg   = (s: number) => s >= 80 ? '#f0fdf4'  : s >= 65 ? '#f0f9ff'  : s >= 45 ? '#fffbe6'  : '#fef2f2';

const RECOMMENDATION_LABELS: Record<string, string> = {
    HIGH_MATCH:     'Strongly Recommended',
    MODERATE_MATCH: 'Recommended',
    LOW_MATCH:      'Partially Suitable',
    NOT_ELIGIBLE:   'Not Eligible',
};

const SCORE_DIM_LABELS: Record<string, string> = {
    domain:        'Domain Alignment',
    geography:     'Geographic Reach',
    financial:     'Financial Capacity',
    experience:    'Experience Record',
    certification: 'Certs & Compliance',
    semantic:      'Semantic Similarity',
    confidence:    'Confidence',
};

// ─── Score Ring ─────────────────────────────────────────────────────────────

function ScoreRing({ score }: { score: number }) {
    const r = 32, circ = 2 * Math.PI * r;
    const color = getScoreColor(score);
    return (
        <div className="relative flex items-center justify-center">
            <svg width={80} height={80} viewBox="0 0 80 80">
                <circle cx={40} cy={40} r={r} fill="none" stroke="#f1f5f9" strokeWidth={8} />
                <motion.circle
                    cx={40} cy={40} r={r} fill="none" stroke={color} strokeWidth={8}
                    strokeDasharray={circ}
                    initial={{ strokeDashoffset: circ }}
                    animate={{ strokeDashoffset: circ - (score / 100) * circ }}
                    transition={{ duration: 1.5, ease: 'easeOut' }}
                    strokeLinecap="round" transform="rotate(-90 40 40)"
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-black text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>{Math.round(score)}</span>
                <span className="text-[8px] font-bold text-slate-400 uppercase">%</span>
            </div>
        </div>
    );
}

// ─── Stat Bar ────────────────────────────────────────────────────────────────

function StatBar({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div className="space-y-1.5">
            <div className="flex justify-between items-center">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{label}</span>
                <span className="text-[10px] font-black" style={{ color }}>{Math.round(value)}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <motion.div className="h-full rounded-full" initial={{ width: 0 }}
                    animate={{ width: `${Math.min(value, 100)}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                    style={{ background: color }}
                />
            </div>
        </div>
    );
}

// ─── Feedback Buttons ────────────────────────────────────────────────────────

type FeedbackSignal = 'interested' | 'not_relevant' | 'submitted' | 'won' | 'lost';

const FEEDBACK_OPTIONS: { signal: FeedbackSignal; label: string; icon: React.ElementType; color: string }[] = [
    { signal: 'interested',   label: 'Interested',   icon: ThumbsUp,  color: 'emerald' },
    { signal: 'not_relevant', label: 'Not Relevant',  icon: ThumbsDown, color: 'slate'  },
    { signal: 'submitted',    label: 'Submitted',    icon: Send,       color: 'blue'   },
    { signal: 'won',          label: 'Won',          icon: Trophy,     color: 'amber'  },
    { signal: 'lost',         label: 'Lost',         icon: Flag,       color: 'red'    },
];

function FeedbackBar({ matchId }: { matchId: string }) {
    const [submitted, setSubmitted] = useState<FeedbackSignal | null>(null);
    const mutation = useMutation({
        mutationFn: (signal: FeedbackSignal) => matchingService.submitFeedback({ match_id: matchId, signal }),
        onMutate: (signal) => setSubmitted(signal),
    });

    return (
        <div className="mt-5 pt-4 border-t border-slate-100">
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3">Your Outcome Signal</p>
            <div className="flex flex-wrap gap-2">
                {FEEDBACK_OPTIONS.map(({ signal, label, icon: Icon, color }) => {
                    const isActive = submitted === signal;
                    const isDisabled = submitted !== null && !isActive;
                    return (
                        <button
                            key={signal}
                            onClick={() => !submitted && mutation.mutate(signal)}
                            disabled={isDisabled}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-wider border transition-all
                                ${isActive
                                    ? `bg-${color}-100 border-${color}-300 text-${color}-700 scale-105`
                                    : `bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100`}
                                disabled:opacity-40 disabled:cursor-not-allowed`}
                        >
                            <Icon className="w-3 h-3" />
                            {isActive && mutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : label}
                        </button>
                    );
                })}
            </div>
            {submitted && !mutation.isPending && (
                <p className="mt-2 text-[10px] text-emerald-600 font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Feedback recorded
                </p>
            )}
        </div>
    );
}

// ─── Match Result Card ───────────────────────────────────────────────────────

function MatchCard({ result, rank }: { result: MatchDetailFull; rank: number }) {
    const [open, setOpen] = useState(false);
    const score = result.weighted_score?.final_score ?? 0;
    const color = getScoreColor(score);
    const isEligible = result.hard_filter_results?.overall_pass ?? true;
    const breakdown = result.weighted_score?.breakdown ?? {};
    const explanation = result.explanation ?? {};

    const dimColors = ['#162f3e', '#0ea5e9', '#c41230', '#8b5cf6', '#10b981', '#f59e0b', '#64748b'];

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: rank * 0.08 }}
            className="pm-card overflow-hidden border-l-4"
            style={{ borderLeftColor: isEligible ? color : '#cbd5e1' }}
        >
            {/* Pipeline badge */}
            <div className="flex items-start justify-between mb-4">
                <span className={`px-2 py-0.5 text-[9px] font-black uppercase tracking-wider rounded-md border
                    ${result.pipeline === 'langgraph'
                        ? 'bg-purple-50 text-purple-700 border-purple-200'
                        : 'bg-slate-50 text-slate-500 border-slate-200'}`}>
                    {result.pipeline === 'langgraph' ? '⚡ LangGraph' : '⚙ Direct'}
                </span>
                {!isEligible && (
                    <span className="px-2 py-0.5 bg-red-50 text-red-600 text-[9px] font-black uppercase rounded-md border border-red-200">
                        Ineligible
                    </span>
                )}
            </div>

            <div className="flex flex-col lg:flex-row gap-6 items-start">
                {/* Score ring */}
                <div className="flex-shrink-0 flex flex-col items-center gap-2">
                    <ScoreRing score={score} />
                    <div className="text-center">
                        <div className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Match Grade</div>
                        <div className="text-[10px] font-bold mt-0.5" style={{ color }}>
                            {RECOMMENDATION_LABELS[result.recommendation] ?? result.recommendation}
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-bold text-[#162f3e] mb-1" style={{ fontFamily: 'Poppins' }}>
                        #{rank} — {result.tender_mongo_id}
                    </h3>
                    <div className="flex flex-wrap gap-3 mb-4 text-[10px] font-bold text-slate-500">
                        <span className="flex items-center gap-1">
                            <Target className="w-3 h-3" />
                            Semantic: {(result.semantic_score * 100).toFixed(1)}%
                        </span>
                        <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {result.matched_at ? new Date(result.matched_at).toLocaleDateString() : '—'}
                        </span>
                        <span className="flex items-center gap-1">
                            {isEligible
                                ? <><CheckCircle2 className="w-3 h-3 text-emerald-500" /><span className="text-emerald-600">Eligible</span></>
                                : <><XCircle className="w-3 h-3 text-red-500" /><span className="text-red-600">Ineligible — {result.hard_filter_results?.failed_check}</span></>}
                        </span>
                    </div>

                    {/* AI Summary */}
                    {explanation.executive_summary && (
                        <div className="p-3 rounded-xl bg-[#162f3e] text-white mb-4">
                            <p className="text-[9px] font-black uppercase tracking-widest opacity-60 mb-1 flex items-center gap-1">
                                <Sparkles className="w-3 h-3" /> AI Executive Summary
                            </p>
                            <p className="text-xs leading-relaxed">{explanation.executive_summary}</p>
                        </div>
                    )}

                    {/* Expand */}
                    <button
                        onClick={() => setOpen(!open)}
                        className="text-[10px] font-black text-[#c41230] hover:underline flex items-center gap-1.5 tracking-widest"
                    >
                        <BarChart3 className="w-3.5 h-3.5" />
                        {open ? 'HIDE BREAKDOWN' : 'VIEW SCORE BREAKDOWN'}
                        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>

                    <AnimatePresence>
                        {open && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }} className="overflow-hidden"
                            >
                                <div className="pt-4 grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-4">
                                    {Object.entries(breakdown).map(([key, val], i) => (
                                        <StatBar
                                            key={key}
                                            label={SCORE_DIM_LABELS[key] ?? key}
                                            value={val as number}
                                            color={dimColors[i % dimColors.length]}
                                        />
                                    ))}
                                </div>

                                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {(explanation.strengths?.length ?? 0) > 0 && (
                                        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-100">
                                            <p className="text-[10px] font-black text-emerald-700 uppercase tracking-widest mb-3 flex items-center gap-2">
                                                <CheckCircle2 className="w-3.5 h-3.5" /> Strengths
                                            </p>
                                            <ul className="space-y-1.5">
                                                {explanation.strengths!.map((s, i) => (
                                                    <li key={i} className="text-xs text-emerald-800 flex items-start gap-2">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1 flex-shrink-0" />{s}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    {(explanation.risk_factors?.length ?? 0) > 0 && (
                                        <div className="p-4 rounded-2xl bg-red-50 border border-red-100">
                                            <p className="text-[10px] font-black text-red-700 uppercase tracking-widest mb-3 flex items-center gap-2">
                                                <AlertCircle className="w-3.5 h-3.5" /> Risk Factors
                                            </p>
                                            <ul className="space-y-1.5">
                                                {explanation.risk_factors!.map((r, i) => (
                                                    <li key={i} className="text-xs text-red-800 flex items-start gap-2">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1 flex-shrink-0" />{r}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <FeedbackBar matchId={result.match_id} />
                </div>
            </div>
        </motion.div>
    );
}

// ─── Polling Status Bar ──────────────────────────────────────────────────────

function PollingStatus({ taskId, onComplete }: { taskId: string; onComplete: (r: MatchDetailFull) => void }) {
    const { data, isError } = useQuery({
        queryKey: ['taskStatus', taskId],
        queryFn: () => matchingService.getTaskStatus(taskId),
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            if (status === 'SUCCESS' || status === 'FAILURE') return false;
            return 3000;
        },
        enabled: !!taskId,
    });

    const status = data?.status as TaskState | undefined;

    // Fire callback once on success
    const [fired, setFired] = useState(false);
    React.useEffect(() => {
        if (status === 'SUCCESS' && data?.result && !fired) {
            setFired(true);
            onComplete(data.result);
        }
    }, [status, data, fired, onComplete]);

    const steps: { key: TaskState | 'queued'; label: string }[] = [
        { key: 'queued',  label: 'Queued' },
        { key: 'PENDING', label: 'Waiting for worker' },
        { key: 'STARTED', label: 'Processing pipeline' },
        { key: 'SUCCESS', label: 'Complete' },
    ];
    const currentIdx = steps.findIndex(s => s.key === status);

    return (
        <div className="pm-card">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#c41230]" /> Pipeline Running — Task {taskId.slice(0, 8)}…
            </p>
            <div className="flex items-center gap-0">
                {steps.map((step, i) => {
                    const done = currentIdx > i;
                    const active = currentIdx === i;
                    return (
                        <React.Fragment key={step.key}>
                            <div className={`flex flex-col items-center gap-1 ${i > 0 ? '' : ''}`}>
                                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-[9px] font-black transition-all
                                    ${done ? 'bg-emerald-500' : active ? 'bg-[#c41230] animate-pulse' : 'bg-slate-200'}`}>
                                    {done ? '✓' : i + 1}
                                </div>
                                <span className={`text-[9px] font-bold whitespace-nowrap ${active ? 'text-[#c41230]' : done ? 'text-emerald-600' : 'text-slate-400'}`}>
                                    {step.label}
                                </span>
                            </div>
                            {i < steps.length - 1 && (
                                <div className={`flex-1 h-0.5 mx-1 mb-4 ${done ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                            )}
                        </React.Fragment>
                    );
                })}
            </div>
            {isError || status === 'FAILURE' ? (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-medium flex items-center gap-2">
                    <XCircle className="w-4 h-4" /> Pipeline failed: {data?.error ?? 'Unknown error'}
                </div>
            ) : null}
        </div>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export const AIMatching = () => {
    const [vendorProfileId, setVendorProfileId] = useState('');
    const [tenderMongoId, setTenderMongoId] = useState('');
    const [useLangGraph, setUseLangGraph] = useState(false);
    const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
    const [results, setResults] = useState<MatchDetailFull[]>([]);

    // Fetch vendor profiles
    const { data: myVendors = [], isLoading: vendorsLoading } = useQuery({
        queryKey: ['vendorProfiles'],
        queryFn: async () => {
            const profiles = await vendorProfileService.list();
            if (profiles.length > 0 && !vendorProfileId) setVendorProfileId(profiles[0].id);
            return profiles;
        },
    });

    // Run match mutation
    const runMutation = useMutation({
        mutationFn: () => matchingService.runMatch({
            vendor_profile_id: vendorProfileId,
            tender_mongo_id: tenderMongoId,
            use_langgraph: useLangGraph,
        }),
        onSuccess: (res) => {
            setActiveTaskId(res.task_id);
            setResults([]);
        },
    });

    const handleComplete = useCallback((result: MatchDetailFull) => {
        setActiveTaskId(null);
        setResults([result]);
    }, []);

    const canRun = vendorProfileId.trim() && tenderMongoId.trim() && !runMutation.isPending && !activeTaskId;

    return (
        <div className="max-w-6xl" style={{ fontFamily: 'DM Sans' }}>
            {/* Header */}
            <div className="mb-10">
                <span className="pm-badge mb-3">Agentic Pipeline v3.0</span>
                <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                    Match <span className="text-[#c41230]">Intelligence</span>
                </h1>
                <p className="text-[#475569] text-lg max-w-2xl">
                    Multi-stage AI pipeline — Hard Filter → Weighted Scoring → LLM Explanation — with full transparency.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Control Panel */}
                <div className="lg:col-span-1">
                    <div className="pm-card sticky top-8 space-y-6">
                        <h2 className="text-sm font-black text-[#162f3e] uppercase tracking-widest flex items-center gap-2">
                            <Target className="w-4 h-4 text-[#c41230]" /> Engine Controls
                        </h2>

                        {/* Vendor selector */}
                        <div>
                            <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">
                                Vendor Profile
                            </label>
                            {vendorsLoading ? (
                                <div className="flex items-center gap-2 text-xs text-slate-400 py-3">
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading…
                                </div>
                            ) : (
                                <select
                                    value={vendorProfileId}
                                    onChange={e => setVendorProfileId(e.target.value)}
                                    className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-xs font-bold text-[#162f3e] focus:outline-none focus:border-[#c41230] transition"
                                >
                                    {myVendors.length === 0 && <option value="">— No profiles —</option>}
                                    {myVendors.map(v => (
                                        <option key={v.id} value={v.id}>
                                            {v.identity?.company_legal_name ?? v.id.slice(0, 12)}
                                        </option>
                                    ))}
                                </select>
                            )}
                        </div>

                        {/* Tender ID input */}
                        <div>
                            <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">
                                Tender MongoDB ID
                            </label>
                            <input
                                type="text"
                                value={tenderMongoId}
                                onChange={e => setTenderMongoId(e.target.value)}
                                placeholder="e.g. 507f1f77bcf86cd799439011"
                                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-xl text-xs font-mono text-[#162f3e] focus:outline-none focus:border-[#c41230] transition placeholder:text-slate-300"
                            />
                        </div>

                        {/* LangGraph toggle */}
                        <div>
                            <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">
                                Pipeline Mode
                            </label>
                            <button
                                onClick={() => setUseLangGraph(!useLangGraph)}
                                className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${
                                    useLangGraph
                                        ? 'border-purple-400 bg-purple-50'
                                        : 'border-slate-200 bg-slate-50 hover:bg-slate-100'
                                }`}
                            >
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${useLangGraph ? 'bg-purple-100' : 'bg-white'}`}>
                                    {useLangGraph ? <Brain className="w-4 h-4 text-purple-600" /> : <Zap className="w-4 h-4 text-slate-400" />}
                                </div>
                                <div className="text-left">
                                    <p className={`text-[10px] font-black uppercase tracking-wider ${useLangGraph ? 'text-purple-700' : 'text-slate-500'}`}>
                                        {useLangGraph ? 'LangGraph Agent' : 'Direct Orchestrator'}
                                    </p>
                                    <p className="text-[9px] text-slate-400">
                                        {useLangGraph ? '6-node stateful graph' : 'Faster, single-pass'}
                                    </p>
                                </div>
                                <div className={`ml-auto w-9 h-5 rounded-full transition-colors relative flex-shrink-0 ${useLangGraph ? 'bg-purple-500' : 'bg-slate-300'}`}>
                                    <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${useLangGraph ? 'translate-x-4' : 'translate-x-0.5'}`} />
                                </div>
                            </button>
                        </div>

                        {/* Run button */}
                        <button
                            onClick={() => runMutation.mutate()}
                            disabled={!canRun}
                            className="w-full pm-btn-primary py-3.5 flex items-center justify-center gap-2 shadow-lg shadow-[#c41230]/20 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            {runMutation.isPending || activeTaskId
                                ? <><Loader2 className="w-4 h-4 animate-spin" /> Running…</>
                                : <><Search className="w-4 h-4" /> RUN MATCH</>}
                        </button>

                        {/* Error */}
                        {runMutation.isError && (
                            <div className="p-3 rounded-xl bg-red-50 border border-red-100 flex items-start gap-2">
                                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                                <p className="text-[10px] font-bold text-red-700">
                                    {(runMutation.error as any)?.response?.data?.detail ?? 'Failed to dispatch task'}
                                </p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Results Area */}
                <div className="lg:col-span-3 space-y-6">
                    {/* Empty state */}
                    {!activeTaskId && results.length === 0 && !runMutation.isPending && (
                        <div className="pm-card py-24 text-center border-dashed border-2 bg-slate-50/30">
                            <div className="w-20 h-20 rounded-3xl bg-white shadow-xl shadow-slate-200/50 flex items-center justify-center mx-auto mb-6">
                                <Sparkles className="w-10 h-10 text-[#c41230]" />
                            </div>
                            <h3 className="text-xl font-bold text-[#162f3e] mb-2" style={{ fontFamily: 'Poppins' }}>Ready to analyse?</h3>
                            <p className="text-slate-500 max-w-sm mx-auto text-sm">
                                Select a vendor profile, enter a Tender MongoDB ID, choose your pipeline, and click Run Match.
                            </p>
                        </div>
                    )}

                    {/* Polling status bar */}
                    {activeTaskId && (
                        <PollingStatus taskId={activeTaskId} onComplete={handleComplete} />
                    )}

                    {/* Results */}
                    {results.map((r, i) => (
                        <MatchCard key={r.match_id ?? i} result={r} rank={i + 1} />
                    ))}
                </div>
            </div>
        </div>
    );
};
