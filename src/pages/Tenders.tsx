import type { Tender } from '../types/tender';
import { TenderCard } from '../components/TenderCard';
import { Filter, Download, Database } from 'lucide-react';

const allTenders: Tender[] = [
    { id: '1', title: 'AI-Driven Supply Chain Platform', organization: 'NeoCorp Global', deadline: '2026-03-15', matchScore: 96, status: 'Open' },
    { id: '2', title: 'Cybersecurity Compliance Audit', organization: 'FinServe Capital', deadline: '2026-04-01', matchScore: 84, status: 'Open' },
    { id: '3', title: 'Cloud Data Center Migration', organization: 'Synapse Technologies', deadline: '2026-03-20', matchScore: 72, status: 'Closed' },
    { id: '4', title: 'Enterprise ERP Modernization', organization: 'Acme Industries', deadline: '2026-05-10', matchScore: 91, status: 'Open' },
    { id: '5', title: 'Autonomous Fleet Management', organization: 'AeroDynamics Inc.', deadline: '2026-04-15', matchScore: 78, status: 'Open' },
    { id: '6', title: 'Blockchain Traceability System', organization: 'Hexagon FinTech', deadline: '2026-06-01', matchScore: 88, status: 'Open' },
];

// PM-style vertical left navigation tabs
const categories = [
    'All Tenders',
    'Safety & Compliance',
    'Document Intelligence',
    'Quality & Audit',
    'Operational Analytics',
    'Finance & Spend',
    'AI Infrastructure',
];

export const Tenders = () => {
    return (
        <div style={{ fontFamily: 'DM Sans' }}>
            {/* Page header */}
            <div className="mb-10">
                <span className="pm-badge mb-3">A complete suite for tender intelligence</span>
                <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                    Tender <span className="text-[#c41230]">Analysis</span>
                </h1>
                <p className="text-[#475569] text-base">AI-ranked tenders matched to your vendor profile in real-time.</p>
            </div>

            {/* PM-style two-column: left vertical tabs + right content */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Left column: Vertical nav tiles like PM */}
                <div className="lg:col-span-1 space-y-2">
                    <div className="flex items-center justify-between mb-4">
                        <Database className="w-4 h-4 text-[#c41230]" />
                        <span className="text-xs text-slate-400 font-medium">Category Filter</span>
                    </div>
                    {categories.map((cat, i) => (
                        <button
                            key={cat}
                            className={`w-full text-left px-5 py-4 rounded-xl border text-sm font-medium transition-all duration-200
                ${i === 0
                                    ? 'bg-[#162f3e] text-white border-[#162f3e] shadow-md'
                                    : 'bg-white border-slate-200 text-[#475569] hover:border-slate-300 hover:bg-slate-50 hover:text-[#162f3e]'
                                }`}
                            style={{ fontFamily: 'DM Sans' }}
                        >
                            {cat}
                        </button>
                    ))}
                </div>

                {/* Right column: Tender cards grid */}
                <div className="lg:col-span-3 space-y-6">
                    {/* Toolbar */}
                    <div className="flex items-center justify-between">
                        <p className="text-sm text-[#475569]">
                            Showing <span className="font-semibold text-[#162f3e]">{allTenders.length}</span> matched tenders
                        </p>
                        <div className="flex gap-3">
                            <button className="pm-btn-secondary text-sm py-2 px-4">
                                <Filter className="w-4 h-4" /> Parameters
                            </button>
                            <button className="pm-btn-primary text-sm py-2 px-5">
                                <Download className="w-4 h-4" /> Export
                            </button>
                        </div>
                    </div>

                    {/* Cards grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                        {allTenders.map(tender => (
                            <TenderCard key={tender.id} tender={tender} />
                        ))}
                    </div>

                    {/* Numbered result badges at the bottom — like PM numbered sequence */}
                    <div className="pt-6 border-t border-slate-200">
                        <div className="flex flex-wrap gap-3">
                            {allTenders.map((t, i) => (
                                <div key={t.id} className="flex items-center gap-2">
                                    <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold bg-[#c41230]" style={{ fontFamily: 'Poppins' }}>
                                        {i + 1}
                                    </div>
                                    <span className="text-xs text-[#475569] truncate max-w-[120px]" style={{ fontFamily: 'DM Sans' }}>{t.title.split(' ').slice(0, 3).join(' ')}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
