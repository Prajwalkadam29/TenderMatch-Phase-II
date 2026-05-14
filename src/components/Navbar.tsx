import { useLocation, Link } from 'react-router-dom';
import { Bell, Search, ChevronRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Navbar = () => {
    const { user } = useAuth();
    const location = useLocation();

    // Calculate breadcrumbs from pathname
    const pathSegments = location.pathname.split('/').filter(Boolean);
    const breadcrumbs = pathSegments.map((segment, index) => {
        const path = `/${pathSegments.slice(0, index + 1).join('/')}`;
        const isLast = index === pathSegments.length - 1;
        const name = segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' ');

        return { name, path, isLast };
    });

    return (
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-slate-200/60">
            <div className="flex h-16 items-center justify-between px-6 lg:px-10">
                {/* Left: Breadcrumbs */}
                <div className="flex items-center gap-2 overflow-hidden">
                    <Link to="/dashboard" className="text-xs font-bold text-slate-400 hover:text-[#162f3e] transition-colors" style={{ fontFamily: 'Poppins' }}>
                        TM
                    </Link>
                    {breadcrumbs.map((bc, i) => (
                        <div key={bc.path} className="flex items-center gap-2">
                            <ChevronRight className="w-3.5 h-3.5 text-slate-300 flex-shrink-0" />
                            <Link
                                to={bc.path}
                                className={`text-xs font-bold whitespace-nowrap transition-colors ${bc.isLast ? 'text-[#162f3e]' : 'text-slate-400 hover:text-[#162f3e]'}`}
                                style={{ fontFamily: 'Poppins' }}
                            >
                                {bc.name}
                            </Link>
                        </div>
                    ))}
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-6">
                    {/* Search Trigger (Mocked) */}
                    <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100/50 border border-slate-200/50 text-slate-400 cursor-pointer hover:bg-slate-100 transition-all">
                        <Search className="w-3.5 h-3.5" />
                        <span className="text-[11px] font-bold uppercase tracking-wider" style={{ fontFamily: 'DM Sans' }}>Search...</span>
                        <span className="ml-4 px-1.5 py-0.5 rounded-md bg-white border border-slate-200 text-[9px] font-bold">⌘K</span>
                    </div>

                    <div className="flex items-center gap-3">
                        <button className="relative p-2 text-slate-400 hover:text-[#c41230] hover:bg-red-50 rounded-xl transition-all">
                            <Bell className="w-4.5 h-4.5" />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-[#c41230] rounded-full border-2 border-white" />
                        </button>

                        <div className="h-4 w-px bg-slate-200 mx-1" />

                        {/* User Profile */}
                        <div className="flex items-center gap-3 pl-1">
                            <div className="hidden lg:block text-right">
                                <p className="text-[11px] font-bold text-[#162f3e] leading-none" style={{ fontFamily: 'Poppins' }}>{user?.name}</p>
                                <p className="text-[9px] text-[#c41230] font-bold uppercase tracking-tighter mt-1" style={{ fontFamily: 'DM Sans' }}>{user?.role}</p>
                            </div>
                            <button className="w-9 h-9 rounded-xl bg-[#162f3e] flex items-center justify-center text-white text-xs font-bold shadow-md hover:scale-105 active:scale-95 transition-all ring-2 ring-white" style={{ fontFamily: 'Poppins' }}>
                                {user?.name?.charAt(0) ?? 'U'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
};
