import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { StatCard } from '../components/StatCard';
import { TenderCard } from '../components/TenderCard';
import { 
    FileText, Send, Trophy, Loader2, 
    Activity, Users, ShieldCheck, ArrowUpRight,
    AlertCircle, Cpu, Briefcase, Sparkles
} from 'lucide-react';
import type { Tender } from '../types/tender';
import { matchingService, type ActivityLog } from '../services/matchingService';
import { vendorProfileService } from '../services/vendorProfileApi';

export const Dashboard = () => {
    const { user, isAdmin } = useAuth();
    const [summary, setSummary] = useState<{
        total_tenders: number;
        total_documents: number;
        total_profiles: number;
        recent_activity: ActivityLog[];
        profile_completeness: number;
        top_matches_count: number;
    } | null>(null);
    const [topTenders, setTopTenders] = useState<Tender[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                // 1. Fetch unified dashboard summary
                const summaryData = await matchingService.getDashboardSummary();
                setSummary(summaryData);

                // 2. Fetch specific matches if user has profiles
                const profiles = await vendorProfileService.list();
                if (profiles.length > 0) {
                    const matches = await matchingService.getTopMatches(profiles[0].id, 4);
                    const mappedTenders: Tender[] = matches.map(m => ({
                        id: m.tender_id,
                        title: m.tender_filename || 'Untitled Tender',
                        organization: (m as any).match_result?.tender_summary?.organization || 'Tender Entity',
                        deadline: (m as any).match_result?.tender_summary?.deadline || new Date().toISOString(),
                        matchScore: Math.round(m.final_score),
                        status: m.eligible ? 'Open' : 'Closed'
                    }));
                    setTopTenders(mappedTenders);
                }
            } catch (err) {
                console.error("Dashboard data fetch failed", err);
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, []);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-[#162f3e]">
                <Loader2 className="w-10 h-10 animate-spin text-[#c41230] mb-4" />
                <p className="text-lg font-medium" style={{ fontFamily: 'Poppins' }}>Tailoring your dashboard...</p>
            </div>
        );
    }

    const profileScore = Math.round(summary?.profile_completeness || 0);

    return (
        <div className="space-y-10" style={{ fontFamily: 'DM Sans' }}>
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <span className="pm-badge mb-3">{isAdmin() ? 'Organization Oversight' : 'Vendor Command Center'}</span>
                    <h1 className="text-4xl font-bold text-[#162f3e] mt-3 mb-2" style={{ fontFamily: 'Poppins' }}>
                        {isAdmin() ? 'Management ' : 'Welcome back, '}
                        <span className="text-[#c41230]">{isAdmin() ? 'Dashboard' : user?.name?.split(' ')[0] || 'User'}</span>
                    </h1>
                    <p className="text-[#475569] text-base leading-relaxed">
                        {isAdmin() 
                            ? 'Monitor team performance and organizational tender pipeline.' 
                            : 'Your AI matching engine has identified new opportunities.'}
                    </p>
                </div>
                {!isAdmin() && profileScore < 100 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-center gap-4 max-w-sm">
                        <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center text-amber-600 flex-shrink-0">
                            <AlertCircle className="w-6 h-6" />
                        </div>
                        <div className="flex-1">
                            <p className="text-[11px] font-bold text-amber-800 uppercase tracking-wider mb-1" style={{ fontFamily: 'Poppins' }}>Profile {profileScore}% Complete</p>
                            <div className="h-1.5 bg-amber-200 rounded-full overflow-hidden">
                                <div className="h-full bg-amber-600" style={{ width: `${profileScore}%` }} />
                            </div>
                            <a href="/profile" className="text-[10px] font-bold text-amber-700 underline mt-2 block">Finish Setup for 100% Match Accuracy →</a>
                        </div>
                    </div>
                )}
            </div>

            {/* Stat cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
                <StatCard title="Indexed Tenders" value={summary?.total_tenders?.toString() || '0'} subtext="Live opportunities" icon={FileText} />
                <StatCard title={isAdmin() ? "Org Documents" : "My Documents"} value={summary?.total_documents?.toString() || '0'} subtext="Total processed" icon={ShieldCheck} />
                <StatCard title={isAdmin() ? "Active Profiles" : "My Profiles"} value={summary?.total_profiles?.toString() || '0'} subtext="Configured entities" icon={Briefcase} />
                <StatCard title="Match Engine" value="v2.1" subtext="pgvector active" icon={Trophy} />
            </div>

            {/* Role-Specific Content */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-7">
                
                {/* LEFT COLUMN: Activity (Admin) or Matches (User) */}
                <div className="lg:col-span-2 space-y-6">
                    <div>
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-2xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>
                                    {isAdmin() ? 'Organization Activity' : 'Top Predictive Matches'}
                                </h2>
                                <p className="text-sm text-[#475569] mt-0.5">
                                    {isAdmin() ? 'Real-time audit logs from your team' : 'AI-ranked opportunities tailored to you'}
                                </p>
                            </div>
                            <a href={isAdmin() ? "/users" : "/tenders"} className="pm-btn-secondary text-sm py-2 px-4">
                                {isAdmin() ? 'Manage Team' : 'View All →'}
                            </a>
                        </div>

                        {isAdmin() ? (
                            <div className="space-y-3">
                                {summary?.recent_activity && summary.recent_activity.length > 0 ? summary.recent_activity.map((log) => (
                                    <div key={log.id} className="pm-card flex items-center justify-between py-4 group">
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center text-slate-400 group-hover:bg-[#162f3e] group-hover:text-white transition-all">
                                                <Activity className="w-5 h-5" />
                                            </div>
                                            <div>
                                                <p className="text-sm font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>
                                                    {log.actor_name || 'System'} <span className="font-normal text-slate-400">performed</span> {log.action?.replace(/\./g, ' ') || 'action'}
                                                </p>
                                                <p className="text-xs text-slate-400 mt-0.5">{log.description || ''}</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-[10px] font-bold text-[#c41230] uppercase">{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                                            <p className="text-[10px] text-slate-300 mt-0.5">{new Date(log.created_at).toLocaleDateString()}</p>
                                        </div>
                                    </div>
                                )) : (
                                    <div className="pm-card py-10 text-center text-slate-400">No recent activity recorded.</div>
                                )}
                            </div>
                        ) : (
                            topTenders.length > 0 ? (
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                                    {topTenders.map(t => <TenderCard key={t.id} tender={t} />)}
                                </div>
                            ) : (
                                <div className="pm-card py-16 text-center bg-slate-50/50">
                                    <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm">
                                        <Sparkles className="w-8 h-8 text-amber-400" />
                                    </div>
                                    <p className="text-[#162f3e] font-semibold" style={{ fontFamily: 'Poppins' }}>No predictive matches yet</p>
                                    <p className="text-sm text-slate-400 mt-1 mb-6">Complete your profile or upload tenders to see results.</p>
                                    <a href="/vendor-profile" className="pm-btn-primary py-2 px-6">Set Up Profile</a>
                                </div>
                            )
                        )}
                    </div>
                </div>

                {/* RIGHT COLUMN: Action Tiles */}
                <div className="space-y-6">
                    <h2 className="text-2xl font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>Quick Actions</h2>
                    <div className="grid grid-cols-1 gap-3">
                        {[
                            { name: 'Upload New Tender', icon: Send, color: 'bg-blue-50 text-blue-600', href: '/upload' },
                            { name: 'Run Batch Match', icon: Cpu, color: 'bg-purple-50 text-purple-600', href: '/match' },
                            { name: 'My Profiles', icon: Briefcase, color: 'bg-emerald-50 text-emerald-600', href: '/profile' },
                        ].map((action) => (
                            <a 
                                key={action.name} 
                                href={action.href}
                                className="pm-card flex items-center justify-between py-4 px-5 hover:border-[#c41230] transition-all group"
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${action.color}`}>
                                        <action.icon className="w-5 h-5" />
                                    </div>
                                    <span className="text-sm font-bold text-[#162f3e]" style={{ fontFamily: 'Poppins' }}>{action.name}</span>
                                </div>
                                <ArrowUpRight className="w-4 h-4 text-slate-300 group-hover:text-[#c41230] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
                            </a>
                        ))}
                    </div>

                    {/* System Status Tile */}
                    <div className="pm-card !bg-[#162f3e] !border-[#162f3e] text-white overflow-hidden relative">
                        <div className="relative z-10">
                            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4" style={{ fontFamily: 'Poppins' }}>System Status</h3>
                            <div className="space-y-3">
                                {[
                                    { label: 'pgvector Index', status: 'Healthy' },
                                    { label: 'Celery Workers', status: 'Active' },
                                    { label: 'Groq LLM', status: 'Online' },
                                ].map(s => (
                                    <div key={s.label} className="flex items-center justify-between">
                                        <span className="text-[11px] font-medium text-slate-300">{s.label}</span>
                                        <div className="flex items-center gap-1.5">
                                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                            <span className="text-[10px] font-bold uppercase">{s.status}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        {/* Decorative logo in background */}
                        <div className="absolute -bottom-6 -right-6 w-24 h-24 bg-white/5 rounded-full flex items-center justify-center">
                            <ShieldCheck className="w-12 h-12 text-white/10" />
                        </div>
                    </div>
                </div>

            </div>

            {/* Footer */}
            <div className="pt-8 border-t border-slate-200 flex justify-between items-center text-[11px] text-slate-400 font-bold uppercase tracking-widest">
                <p>© 2026 TenderMatch AI · Professional Grade Infrastructure</p>
                <div className="flex gap-6">
                    <a href="#" className="hover:text-[#c41230] transition-colors">Privacy</a>
                    <a href="#" className="hover:text-[#c41230] transition-colors">Security Audit</a>
                </div>
            </div>
        </div>
    );
};
