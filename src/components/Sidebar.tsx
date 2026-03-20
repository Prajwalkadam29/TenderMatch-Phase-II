import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
    LayoutDashboard, FileText, User, BarChart2,
    Users, Building2, CreditCard, LifeBuoy, LogOut,
    Upload, Cpu, ClipboardList,
} from 'lucide-react';

interface NavItem {
    name: string;
    href: string;
    icon: React.ElementType;
    roles: string[];
}

const navigation: NavItem[] = [
    { name: 'Dashboard',       href: '/dashboard',  icon: LayoutDashboard, roles: ['USER', 'ADMIN1', 'CUSTOMER_SUPPORT'] },
    { name: 'Tenders',         href: '/tenders',    icon: FileText,        roles: ['USER', 'ADMIN1'] },
    { name: 'Upload Docs',     href: '/upload',     icon: Upload,          roles: ['USER', 'ADMIN1'] },
    { name: 'AI Matching',     href: '/match',          icon: Cpu,           roles: ['USER', 'ADMIN1'] },
    { name: 'Vendor Profile',  href: '/vendor-profile', icon: ClipboardList, roles: ['USER', 'ADMIN1'] },
    { name: 'Profile',         href: '/profile',        icon: User,          roles: ['USER', 'ADMIN1'] },
    { name: 'Analytics',       href: '/analytics',  icon: BarChart2,       roles: ['ADMIN1'] },
    { name: 'Users',           href: '/users',      icon: Users,           roles: ['ADMIN1'] },
    { name: 'Dashboard',       href: '/dashboard',  icon: LayoutDashboard, roles: ['SUPERADMIN'] },
    { name: 'Organizations',   href: '/admin/organizations', icon: Building2, roles: ['SUPERADMIN'] },
    { name: 'Subscriptions',   href: '/admin/subscriptions', icon: CreditCard, roles: ['SUPERADMIN'] },
    { name: 'Support View',    href: '/support/view/1', icon: LifeBuoy,    roles: ['CUSTOMER_SUPPORT'] },
];

export const Sidebar = () => {
    const { user, hasRole, logout } = useAuth();
    const location = useLocation();
    const filtered = navigation.filter(item => hasRole(item.roles as any));

    return (
        <aside className="flex flex-col h-full w-64 bg-white border-r border-slate-200 shadow-sm z-20 flex-shrink-0">
            {/* Brand */}
            <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-100">
                {/* PM-style code logo */}
                <div className="flex items-center justify-center w-9 h-9 rounded-md bg-[#162f3e]">
                    <span className="text-white font-bold text-sm font-mono" style={{ fontFamily: 'Poppins' }}>≡</span>
                </div>
                <div>
                    <p className="font-bold text-[#162f3e] leading-none" style={{ fontFamily: 'Poppins', fontSize: 15 }}>TenderMatch</p>
                    <p className="text-[10px] text-[#c41230] font-medium mt-0.5" style={{ fontFamily: 'DM Sans' }}>Live & Listening!</p>
                </div>
            </div>

            {/* Nav items */}
            <nav className="flex-1 py-4 px-3 overflow-y-auto space-y-1">
                {filtered.map((item) => {
                    const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/');
                    return (
                        <Link
                            key={item.name + item.href}
                            to={item.href}
                            className={`
                flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200
                ${isActive
                                    ? 'bg-[#162f3e] text-white shadow-md'
                                    : 'text-[#475569] hover:bg-slate-50 hover:text-[#162f3e]'}
              `}
                            style={{ fontFamily: 'DM Sans' }}
                        >
                            <item.icon
                                className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-[#c41230]' : 'text-slate-400'}`}
                            />
                            {item.name}
                            {isActive && (
                                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[#c41230]" />
                            )}
                        </Link>
                    );
                })}
            </nav>

            {/* User footer */}
            <div className="border-t border-slate-100 p-4 space-y-3">
                <div className="flex items-center gap-3 px-2 py-2 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="w-8 h-8 rounded-full bg-[#c41230] flex items-center justify-center text-white text-xs font-bold flex-shrink-0" style={{ fontFamily: 'Poppins' }}>
                        {user?.name?.charAt(0) ?? 'U'}
                    </div>
                    <div className="min-w-0">
                        <p className="text-sm font-semibold text-[#162f3e] truncate" style={{ fontFamily: 'Poppins' }}>{user?.name}</p>
                        <p className="text-xs text-[#c41230] font-medium truncate" style={{ fontFamily: 'DM Sans' }}>{user?.role}</p>
                    </div>
                </div>
                <button
                    onClick={logout}
                    className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:bg-red-50 hover:text-[#c41230] transition-colors duration-200"
                    style={{ fontFamily: 'DM Sans' }}
                >
                    <LogOut className="w-4 h-4" />
                    Sign Out
                </button>
            </div>
        </aside>
    );
};
