import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';
import { FloatingDots } from './FloatingDots';

export const Layout = () => {
    return (
        <div className="flex h-screen overflow-hidden bg-[#f1f5f9]" style={{ fontFamily: 'DM Sans' }}>
            {/* PM-style floating background dots */}
            <FloatingDots />

            <Sidebar />

            <div className="flex-1 flex flex-col relative z-10 overflow-hidden">
                <Navbar />
                <main className="flex-1 overflow-y-auto px-6 py-8 lg:px-10 lg:py-10 max-w-7xl w-full mx-auto">
                    <Outlet />
                </main>
            </div>
        </div>
    );
};
