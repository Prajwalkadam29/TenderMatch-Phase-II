import { Bell, Search } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Navbar = () => {
    const { user } = useAuth();

    return (
        <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200 shadow-sm">
            <div className="flex h-16 items-center justify-between px-6 lg:px-10">
                {/* Search */}
                <div className="flex items-center flex-1 max-w-sm">
                    <div className="relative w-full group">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-[#c41230] transition-colors" />
                        <input
                            type="text"
                            placeholder="Search tenders, organizations..."
                            className="w-full bg-slate-50 border border-slate-200 rounded-xl py-2 pl-9 pr-4 text-sm text-[#162f3e] placeholder:text-slate-400 focus:outline-none focus:border-[#c41230] focus:ring-2 focus:ring-[#c41230]/10 transition-all"
                            style={{ fontFamily: 'DM Sans' }}
                        />
                    </div>
                </div>

                {/* Right side */}
                <div className="flex items-center gap-4 ml-4">
                    {/* Notification bell */}
                    <button className="relative p-2 text-slate-400 hover:text-[#c41230] hover:bg-red-50 rounded-xl transition-colors">
                        <Bell className="w-5 h-5" />
                        <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#c41230] rounded-full" />
                    </button>

                    <div className="h-6 w-px bg-slate-200" />

                    {/* User chip — matches PM's minimal user presence */}
                    <button className="flex items-center gap-2.5 text-sm font-medium text-[#162f3e] hover:text-[#c41230] transition-colors" style={{ fontFamily: 'DM Sans' }}>
                        <div className="w-8 h-8 rounded-full bg-[#c41230] flex items-center justify-center text-white text-xs font-bold flex-shrink-0" style={{ fontFamily: 'Poppins' }}>
                            {user?.name?.charAt(0) ?? 'U'}
                        </div>
                        <span className="hidden md:inline">{user?.name}</span>
                    </button>
                </div>
            </div>
        </header>
    );
};
