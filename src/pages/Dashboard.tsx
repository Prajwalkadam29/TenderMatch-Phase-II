import { useAuth } from '../context/AuthContext';
import { StatCard } from '../components/StatCard';
import { TenderCard } from '../components/TenderCard';
import { FileText, ThumbsUp, Send, Trophy } from 'lucide-react';
import type { Tender } from '../types/tender';

const mockTenders: Tender[] = [
    { id: '1', title: 'AI-Driven Supply Chain Platform', organization: 'NeoCorp Global', deadline: '2026-03-15', matchScore: 96, status: 'Open' },
    { id: '2', title: 'Cybersecurity Compliance Audit', organization: 'FinServe Capital', deadline: '2026-04-01', matchScore: 84, status: 'Open' },
    { id: '3', title: 'Cloud Data Center Migration', organization: 'Synapse Technologies', deadline: '2026-03-20', matchScore: 72, status: 'Closed' },
];

const recentNotifications = [
    { id: 1, text: 'New tender matched: AI-Driven Supply Chain Platform', time: '2 min ago', type: 'match' },
    { id: 2, text: 'Feedback submitted for NeuralNet Procurement Tender', time: '1 hr ago', type: 'feedback' },
    { id: 3, text: 'Match score updated for Cybersecurity Audit', time: '3 hrs ago', type: 'update' },
];

export const Dashboard = () => {
    const { user } = useAuth();

    return (
        <div className="space-y-10" style={{ fontFamily: 'DM Sans' }}>
            {/* Page header — PM section heading style */}
            <div>
                <span className="pm-badge mb-3">Live & Listening!</span>
                <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                    Welcome back,{' '}
                    <span className="text-[#c41230]">{user?.name?.split(' ')[0]}</span>
                </h1>
                <p className="text-[#475569] text-base leading-relaxed">
                    Your AI matching engine is active. Here's your real-time overview.
                </p>
            </div>

            {/* Stat cards — 4-column PM style */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
                <StatCard title="Total Matched Tenders" value="156" subtext="+12% from last month" icon={FileText} />
                <StatCard title="Interested" value="43" subtext="Awaiting your review" icon={ThumbsUp} />
                <StatCard title="Submitted" value="12" subtext="3 awaiting decision" icon={Send} />
                <StatCard title="Won" value="4" subtext="$1.2M total contract value" icon={Trophy} />
            </div>

            {/* Two-column layout: Top Matches + Notifications */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-7">
                {/* Top Matches — 2/3 width */}
                <div className="lg:col-span-2 space-y-5">
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-2xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>Top Predictive Matches</h2>
                            <p className="text-sm text-[#475569] mt-0.5">AI-ranked high-confidence recommendations</p>
                        </div>
                        <a href="/tenders" className="pm-btn-secondary text-sm py-2 px-4">
                            View all →
                        </a>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-5">
                        {mockTenders.slice(0, 2).map(t => <TenderCard key={t.id} tender={t} />)}
                    </div>
                </div>

                {/* Recent Notifications sidebar — like PM's vertical nav tiles */}
                <div>
                    <h2 className="text-2xl font-bold text-[#162f3e] mb-4" style={{ fontFamily: 'Poppins' }}>Notifications</h2>
                    <div className="space-y-3">
                        {recentNotifications.map((n, i) => (
                            <div key={n.id} className={`pm-card flex items-start gap-3 py-4 px-5 cursor-pointer ${i === 0 ? '!bg-[#162f3e] !border-[#162f3e]' : ''}`}>
                                <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 mt-1.5 ${i === 0 ? 'bg-[#c41230]' : 'bg-slate-300'}`} />
                                <div>
                                    <p className={`text-sm font-medium leading-snug ${i === 0 ? 'text-white' : 'text-[#162f3e]'}`} style={{ fontFamily: 'DM Sans' }}>
                                        {n.text}
                                    </p>
                                    <p className={`text-xs mt-1 ${i === 0 ? 'text-slate-400' : 'text-slate-400'}`} style={{ fontFamily: 'DM Sans' }}>
                                        {n.time}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Quick Feedback */}
                    <h2 className="text-2xl font-bold text-[#162f3e] mt-8 mb-4" style={{ fontFamily: 'Poppins' }}>Quick Feedback</h2>
                    <div className="space-y-2">
                        {['Mark as Interested', 'Not Relevant', 'Submitted Proposal'].map(label => (
                            <button key={label} className="pm-btn-secondary w-full justify-start text-sm py-3">
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Section footer divider like PM */}
            <div className="border-t border-slate-200 pt-6">
                <div className="flex items-center justify-between">
                    <p className="text-xs text-slate-400">TenderMatch AI Engine v2.0 · All data live & listening</p>
                    <span className="pm-badge">Expected Outcomes: Faster wins, better ROI</span>
                </div>
            </div>
        </div>
    );
};
