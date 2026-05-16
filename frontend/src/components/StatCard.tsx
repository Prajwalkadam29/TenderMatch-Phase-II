interface StatCardProps {
    title: string;
    value: string | number;
    subtext: string;
    icon: React.ElementType;
}

export const StatCard = ({ title, value, subtext, icon: Icon }: StatCardProps) => {
    return (
        <div className="pm-card group">
            {/* Icon box — red background like PM */}
            <div className="pm-icon-box mb-5">
                <Icon className="w-5 h-5" />
            </div>

            <div>
                <p className="text-sm font-medium text-[#475569] mb-1" style={{ fontFamily: 'DM Sans' }}>{title}</p>
                <p className="text-3xl font-bold text-[#162f3e] mb-1" style={{ fontFamily: 'Poppins' }}>{value}</p>
                <p className="text-xs text-slate-400" style={{ fontFamily: 'DM Sans' }}>{subtext}</p>
            </div>

            {/* Bottom accent line on hover */}
            <div className="h-0.5 bg-[#c41230] mt-5 scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left rounded-full" />
        </div>
    );
};
