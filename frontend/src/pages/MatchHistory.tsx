import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    History, Filter, ChevronLeft, ChevronRight,
    Loader2, AlertCircle, FileText, Target
} from 'lucide-react';
import { matchingService } from '../services/matchingService';
import { vendorProfileService } from '../services/vendorProfileApi';

const RECOMMENDATION_LABELS: Record<string, string> = {
    HIGH_MATCH: 'Strongly Recommended',
    MODERATE_MATCH: 'Recommended',
    LOW_MATCH: 'Partially Suitable',
    NOT_ELIGIBLE: 'Not Eligible',
};

const getScoreColor = (s: number) => s >= 80 ? 'text-emerald-600 bg-emerald-50 border-emerald-200' : s >= 65 ? 'text-sky-600 bg-sky-50 border-sky-200' : s >= 45 ? 'text-amber-600 bg-amber-50 border-amber-200' : 'text-red-600 bg-red-50 border-red-200';

export const MatchHistory = () => {
    const [vendorProfileId, setVendorProfileId] = useState<string>('');
    const [page, setPage] = useState(0);
    const limit = 20;

    const { data: myVendors = [] } = useQuery({
        queryKey: ['vendorProfiles'],
        queryFn: () => vendorProfileService.list(),
    });

    const { data: history = [], isLoading, isError } = useQuery({
        queryKey: ['matchHistory', vendorProfileId, page],
        queryFn: () => matchingService.getHistory({
            vendor_profile_id: vendorProfileId || undefined,
            limit,
            offset: page * limit
        }),
    });

    return (
        <div className="max-w-6xl" style={{ fontFamily: 'DM Sans' }}>
            <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <span className="pm-badge mb-3 flex items-center gap-2 w-fit">
                        <History className="w-3.5 h-3.5" /> History Log
                    </span>
                    <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                        Match <span className="text-[#c41230]">History</span>
                    </h1>
                    <p className="text-[#475569] text-lg max-w-2xl">
                        Review all past AI matching cycles, filtering by vendor profile to trace your organizational success rate.
                    </p>
                </div>
            </div>

            <div className="pm-card space-y-6">
                <div className="flex flex-col sm:flex-row gap-4 justify-between items-center pb-6 border-b border-slate-100">
                    <div className="flex items-center gap-3 w-full sm:w-auto">
                        <Filter className="w-4 h-4 text-slate-400" />
                        <select
                            value={vendorProfileId}
                            onChange={(e) => { setVendorProfileId(e.target.value); setPage(0); }}
                            className="w-full sm:w-64 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold text-[#162f3e] focus:outline-none focus:border-[#c41230]"
                        >
                            <option value="">All Profiles</option>
                            {myVendors.map(v => (
                                <option key={v.id} value={v.id}>{v.identity?.company_legal_name ?? v.id.slice(0, 8)}</option>
                            ))}
                        </select>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setPage(p => Math.max(0, p - 1))}
                            disabled={page === 0}
                            className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 transition"
                        >
                            <ChevronLeft className="w-4 h-4 text-slate-500" />
                        </button>
                        <span className="text-xs font-bold text-slate-400 px-2">Page {page + 1}</span>
                        <button
                            onClick={() => setPage(p => p + 1)}
                            disabled={history.length < limit}
                            className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 transition"
                        >
                            <ChevronRight className="w-4 h-4 text-slate-500" />
                        </button>
                    </div>
                </div>

                {isLoading ? (
                    <div className="py-20 flex flex-col items-center justify-center text-slate-400">
                        <Loader2 className="w-8 h-8 animate-spin mb-4 text-[#c41230]" />
                        <p className="text-sm font-bold">Loading match history...</p>
                    </div>
                ) : isError ? (
                    <div className="py-20 flex flex-col items-center justify-center text-red-500">
                        <AlertCircle className="w-8 h-8 mb-4" />
                        <p className="text-sm font-bold">Failed to load history</p>
                    </div>
                ) : history.length === 0 ? (
                    <div className="py-20 flex flex-col items-center justify-center text-slate-400">
                        <FileText className="w-12 h-12 mb-4 text-slate-200" />
                        <p className="text-sm font-bold">No match history found</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-slate-200 text-[10px] font-black uppercase tracking-widest text-slate-400">
                                    <th className="py-3 px-4">Date</th>
                                    <th className="py-3 px-4">Tender ID</th>
                                    <th className="py-3 px-4">Score</th>
                                    <th className="py-3 px-4">Recommendation</th>
                                    <th className="py-3 px-4 text-center">Pipeline</th>
                                </tr>
                            </thead>
                            <tbody>
                                {history.map((row) => (
                                    <tr key={row.match_id} className="border-b border-slate-50 hover:bg-slate-50/50 transition group">
                                        <td className="py-4 px-4 text-xs font-medium text-slate-500">
                                            {new Date(row.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="py-4 px-4">
                                            <div className="text-sm font-bold text-[#162f3e] group-hover:text-[#c41230] transition flex items-center gap-2">
                                                <Target className="w-3.5 h-3.5 text-slate-300" />
                                                {row.tender_id}
                                            </div>
                                        </td>
                                        <td className="py-4 px-4">
                                            <span className={`inline-block px-2.5 py-1 rounded-lg text-[10px] font-black border ${getScoreColor(row.final_score)}`}>
                                                {Math.round(row.final_score)}%
                                            </span>
                                        </td>
                                        <td className="py-4 px-4">
                                            <span className="text-xs font-bold text-slate-700">
                                                {RECOMMENDATION_LABELS[row.recommendation] ?? row.recommendation}
                                            </span>
                                        </td>
                                        <td className="py-4 px-4 text-center">
                                            <span className={`px-2 py-0.5 text-[9px] font-black uppercase tracking-wider rounded-md border
                                                ${row.pipeline === 'langgraph' ? 'bg-purple-50 text-purple-700 border-purple-200' : 'bg-slate-50 text-slate-500 border-slate-200'}`}>
                                                {row.pipeline}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};
