import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
    LayoutDashboard, FileText, User, BarChart2,
    Users, Building2, CreditCard, LifeBuoy, LogOut,
    Upload, Cpu, ClipboardList, ChevronRight, Moon, Sun, Briefcase
} from 'lucide-react';

interface NavItem {
    name: string;
    href: string;
    icon: React.ElementType;
    roles: string[];
}

interface NavGroup {
    groupName: string;
    items: NavItem[];
}

const navGroups: NavGroup[] = [
    {
        groupName: 'Discovery',
        items: [
            { name: 'Dashboard',   href: '/dashboard', icon: LayoutDashboard, roles: ['USER', 'ADMIN1', 'CUSTOMER_SUPPORT'] },
            { name: 'AI Matching', href: '/match',     icon: Cpu,             roles: ['USER', 'ADMIN1'] },
            { name: 'Tenders',     href: '/tenders',   icon: FileText,        roles: ['USER', 'ADMIN1'] },
        ]
    },
    {
        groupName: 'Workspace',
        items: [
            { name: 'Upload Docs',    href: '/upload',         icon: Upload,        roles: ['USER', 'ADMIN1'] },
            { name: 'Vendor Profile', href: '/vendor-profile', icon: ClipboardList,  roles: ['USER', 'ADMIN1'] },
            { name: 'My Profiles',    href: '/profile',        icon: Briefcase,     roles: ['USER', 'ADMIN1'] },
            { name: 'User Settings',  href: '/settings',       icon: User,          roles: ['USER', 'ADMIN1', 'SUPERADMIN', 'CUSTOMER_SUPPORT'] },
        ]
    },
    {
        groupName: 'Administration',
        items: [
            { name: 'Deep Analytics', href: '/analytics',      icon: BarChart2,      roles: ['ADMIN1'] },
            { name: 'Team Members',   href: '/users',          icon: Users,          roles: ['ADMIN1'] },
            { name: 'Dashboard',      href: '/dashboard',      icon: LayoutDashboard,roles: ['SUPERADMIN'] },
            { name: 'Organizations',  href: '/admin/organizations', icon: Building2, roles: ['SUPERADMIN'] },
            { name: 'Subscriptions',  href: '/admin/subscriptions', icon: CreditCard,roles: ['SUPERADMIN'] },
            { name: 'Support View',   href: '/support/view/1', icon: LifeBuoy,      roles: ['CUSTOMER_SUPPORT'] },
        ]
    }
];

export const Sidebar = () => {
    const { user, hasRole, logout, theme, toggleTheme } = useAuth();
    const location = useLocation();

    const renderItem = (item: NavItem) => {
        if (!hasRole(item.roles as any)) return null;
        
        const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/');
        
        return (
            <Link
                key={item.name + item.href}
                to={item.href}
                className={`
                    flex items-center gap-3 px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-200 group
                    ${isActive 
                        ? 'pm-nav-tile-active' 
                        : 'text-[var(--pm-text-muted)] hover:bg-[var(--pm-bg-alt)] hover:text-[var(--pm-text)]'}
                `}
                style={{ fontFamily: 'DM Sans' }}
            >
                <item.icon 
                    className={`w-4 h-4 flex-shrink-0 transition-colors ${isActive ? 'text-[#c41230]' : 'text-slate-400 group-hover:text-[#c41230]'}`} 
                />
                <span className="flex-1">{item.name}</span>
                {isActive && (
                    <ChevronRight className="w-3.5 h-3.5 opacity-60" />
                )}
            </Link>
        );
    };

    return (
        <aside className="flex flex-col h-full w-64 bg-[var(--pm-white)] border-r border-[var(--pm-border)] shadow-sm z-20 flex-shrink-0 transition-colors">
            {/* Brand */}
            <div className="flex items-center gap-3 px-6 py-6 border-b border-[var(--pm-border)] mb-2">
                <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-[#162f3e] shadow-inner">
                    <span className="text-white font-bold text-lg" style={{ fontFamily: 'Poppins' }}>T</span>
                </div>
                <div>
                    <p className="font-bold text-[var(--pm-text)] tracking-tight" style={{ fontFamily: 'Poppins', fontSize: 16 }}>TenderMatch</p>
                    <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        <p className="text-[10px] text-[#c41230] font-bold uppercase tracking-widest" style={{ fontFamily: 'DM Sans' }}>Live</p>
                    </div>
                </div>
            </div>

            {/* Nav groups */}
            <nav className="flex-1 py-4 px-4 overflow-y-auto space-y-7 custom-scrollbar">
                {navGroups.map((group) => {
                    const visibleItems = group.items.filter(i => hasRole(i.roles as any));
                    if (visibleItems.length === 0) return null;

                    return (
                        <div key={group.groupName} className="space-y-2">
                            <h3 className="px-4 text-[10px] font-bold text-[var(--pm-text-muted)] uppercase tracking-[0.15em]" style={{ fontFamily: 'Poppins' }}>
                                {group.groupName}
                            </h3>
                            <div className="space-y-1">
                                {group.items.map(renderItem)}
                            </div>
                        </div>
                    );
                })}
            </nav>

            {/* Theme Toggle & User footer */}
            <div className="p-4 bg-[var(--pm-bg-alt)] border-t border-[var(--pm-border)] transition-colors">
                
                <button 
                    onClick={toggleTheme}
                    className="w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-[11px] font-bold text-[var(--pm-text-muted)] hover:bg-[var(--pm-white)] border border-transparent hover:border-[var(--pm-border)] transition-all mb-4"
                >
                    <div className="flex items-center gap-2">
                        {theme === 'light' ? <Moon className="w-3.5 h-3.5" /> : <Sun className="w-3.5 h-3.5" />}
                        {theme === 'light' ? 'DARK MODE' : 'LIGHT MODE'}
                    </div>
                    <div className={`w-8 h-4 rounded-full p-0.5 transition-colors ${theme === 'dark' ? 'bg-[#c41230]' : 'bg-slate-300'}`}>
                        <div className={`w-3 h-3 rounded-full bg-white transition-transform ${theme === 'dark' ? 'translate-x-4' : 'translate-x-0'}`} />
                    </div>
                </button>

                <div className="px-3 py-3 rounded-2xl bg-[var(--pm-white)] border border-[var(--pm-border)] shadow-sm mb-3">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-[#c41230] flex items-center justify-center text-white text-sm font-bold shadow-md" style={{ fontFamily: 'Poppins' }}>
                            {user?.name?.charAt(0) ?? 'U'}
                        </div>
                        <div className="min-w-0">
                            <p className="text-sm font-bold text-[var(--pm-text)] truncate" style={{ fontFamily: 'Poppins' }}>{user?.name}</p>
                            <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-[var(--pm-red-light)] text-[10px] font-bold text-[#c41230] uppercase border border-red-100/10 mt-0.5">
                                {user?.role}
                            </span>
                        </div>
                    </div>
                </div>
                <button
                    onClick={logout}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-xs font-bold text-[var(--pm-text-muted)] hover:bg-red-50/10 hover:text-[#c41230] border border-transparent hover:border-red-100/20 transition-all duration-200"
                    style={{ fontFamily: 'DM Sans' }}
                >
                    <LogOut className="w-4 h-4" />
                    SIGN OUT
                </button>
            </div>
        </aside>
    );
};

