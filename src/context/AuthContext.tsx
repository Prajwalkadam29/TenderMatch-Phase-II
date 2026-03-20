import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { User, Role } from '../types/user';

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string, user: User) => void;
    logout: () => void;
    isAuthenticated: boolean;
    hasRole: (roles: Role[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<User | null>(() => {
        const stored = localStorage.getItem('user');
        return stored ? JSON.parse(stored) : null;
    });
    const [token, setToken] = useState<string | null>(() => {
        return localStorage.getItem('access_token') || null;
    });

    useEffect(() => {

        // Listener for auto-logout
        const handleUnauthorized = () => {
            logout();
        };

        window.addEventListener('auth:unauthorized', handleUnauthorized);
        return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
    }, []);

    const login = (newToken: string, loggedInUser: User) => {
        setToken(newToken);
        setUser(loggedInUser);
        localStorage.setItem('access_token', newToken);
        localStorage.setItem('user', JSON.stringify(loggedInUser));
    };

    const logout = () => {
        setToken(null);
        setUser(null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
    };

    const hasRole = (roles: Role[]) => {
        if (!user) return false;
        return roles.includes(user.role);
    };

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token, hasRole }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
