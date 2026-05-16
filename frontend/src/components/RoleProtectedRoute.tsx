import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import type { Role } from '../types/user';

import type { ReactNode } from 'react';

interface RoleProtectedRouteProps {
    allowedRoles: Role[];
    children: ReactNode;
}

export const RoleProtectedRoute = ({ allowedRoles, children }: RoleProtectedRouteProps) => {
    const { isAuthenticated, hasRole } = useAuth();
    const location = useLocation();

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (!hasRole(allowedRoles)) {
        return (
            <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
                <div className="text-center p-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-sm w-full mx-4">
                    <h2 className="text-2xl font-bold text-red-600 dark:text-red-400 mb-4">Access Denied</h2>
                    <p className="text-gray-600 dark:text-gray-300">Insufficient Permissions</p>
                </div>
            </div>
        );
    }

    return children;
};
