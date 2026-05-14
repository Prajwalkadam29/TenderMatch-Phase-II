import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute = () => {
    const { isAuthenticated, isInitializing } = useAuth();
    const location = useLocation();

    // While we are attempting to restore the session from the refresh cookie,
    // show a blank loading state — do NOT redirect yet.
    if (isInitializing) {
        return (
            <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                height: '100vh', background: '#f8fafc',
            }}>
                <div style={{ textAlign: 'center', color: '#64748b' }}>
                    <div style={{
                        width: 40, height: 40, border: '3px solid #e2e8f0',
                        borderTopColor: '#c41230', borderRadius: '50%',
                        animation: 'spin 0.8s linear infinite', margin: '0 auto 12px',
                    }} />
                    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                    <p style={{ fontSize: 14, margin: 0 }}>Restoring session…</p>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return <Outlet />;
};
