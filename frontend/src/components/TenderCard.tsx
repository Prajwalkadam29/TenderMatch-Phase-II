import type { Tender } from '../types/tender';
import { Link } from 'react-router-dom';
import { Calendar, ArrowRight, Building2 } from 'lucide-react';

const statusStyles: Record<string, string> = {
    Open: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    Closed: 'bg-slate-100 text-slate-500 border-slate-200',
    Awarded: 'bg-blue-50 text-blue-700 border-blue-200',
};

export const TenderCard = ({ tender }: { tender: Tender }) => {
    const isHigh = tender.matchScore >= 80;

    return (
        <div className="pm-card group flex flex-col justify-between h-full">
            {/* Header */}
            <div>
                {/* Icon + status */}
                <div className="flex items-start justify-between mb-4">
                    <div className="pm-icon-box">
                        <Building2 className="w-5 h-5" />
                    </div>
                    <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${statusStyles[tender.status] ?? ''}`} style={{ fontFamily: 'DM Sans' }}>
                        {tender.status}
                    </span>
                </div>

                {/* Title */}
                <h3 className="text-base font-bold text-[#162f3e] mb-1 group-hover:text-[#c41230] transition-colors" style={{ fontFamily: 'Poppins' }}>
                    {tender.title}
                </h3>
                <p className="text-sm text-[#475569] mb-5" style={{ fontFamily: 'DM Sans' }}>{tender.organization}</p>

                {/* Match Score — PM numbered badge style */}
                <div className="rounded-xl bg-slate-50 border border-slate-100 p-4 mb-4">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-xs font-medium text-[#475569]" style={{ fontFamily: 'DM Sans' }}>AI Match Score</span>
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${isHigh ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`} style={{ fontFamily: 'Poppins' }}>
                            {tender.matchScore}%
                        </span>
                    </div>
                    <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div
                            className={`h-full rounded-full transition-all duration-700 ${isHigh ? 'bg-emerald-500' : tender.matchScore > 50 ? 'bg-amber-400' : 'bg-[#c41230]'}`}
                            style={{ width: `${tender.matchScore}%` }}
                        />
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                <div className="flex items-center gap-1.5 text-xs text-slate-400" style={{ fontFamily: 'DM Sans' }}>
                    <Calendar className="w-3.5 h-3.5 text-[#c41230]" />
                    <span>{new Date(tender.deadline).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                </div>
                <Link
                    to={`/tenders/${tender.id}`}
                    className="flex items-center gap-1 text-sm font-semibold text-[#c41230] hover:text-[#a50e28] transition-colors group/link"
                    style={{ fontFamily: 'DM Sans' }}
                >
                    View
                    <ArrowRight className="w-4 h-4 transform group-hover/link:translate-x-0.5 transition-transform" />
                </Link>
            </div>
        </div>
    );
};
