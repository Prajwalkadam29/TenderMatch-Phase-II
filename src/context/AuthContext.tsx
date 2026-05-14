/**
 * AuthContext.tsx
 * ---------------
 * Global authentication state with automatic token refresh.
 *
 * Token strategy:
 * - Access token: short-lived (15 min), stored in memory only (not localStorage)
 *   → XSS-safe: JS cannot steal what isn't in storage
 * - Refresh token: long-lived (7 days), stored in httpOnly cookie by the server
 *   → XSS-safe: JS cannot read httpOnly cookies
 * - Auto-refresh:
 * - On mount: attempt to restore session via /auth/refresh (uses the cookie)
 * - 2 minutes before expiry: proactively refresh the access token
 * - On 401 from any API call: trigger refresh and retry
 */

import {
    createContext, useContext, useState, useEffect, useRef,
    useCallback,
} from 'react';
import type { ReactNode } from 'react';
import type { User, Role } from '../types/user';
import api, { setApiToken } from '../services/api';

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string, user: User) => void;
    logout: () => Promise<void>;
    isAuthenticated: boolean;
    hasRole: (roles: Role[]) => boolean;
    isAdmin: () => boolean;
    isInitializing: boolean;
    updateProfile: (data: { name?: string }) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const REFRESH_BUFFER_MS = 2 * 60 * 1000; // Refresh 2 min before expiry

/** Parse the JWT exp claim without a library */
function getTokenExpiry(token: string): number | null {
    try {
        const [, payload] = token.split('.');
        const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
        return decoded.exp ? decoded.exp * 1000 : null; // Convert to ms
    } catch {
        return null;
    }
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    // Access token lives ONLY in memory — never in localStorage
    const [token, setToken] = useState<string | null>(null);
    const [user, setUser] = useState<User | null>(null);
    const [isInitializing, setIsInitializing] = useState(true);

    const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const updateProfile = useCallback(async (payload: { name?: string }) => {
        try {
            const { data } = await api.put('/organization/me', payload);
            setUser(data);
        } catch (err) {
            console.error('Failed to update profile', err);
            throw err;
        }
    }, []);

    /** Clear the scheduled refresh timer */
    const clearRefreshTimer = useCallback(() => {
        if (refreshTimerRef.current) {
            clearTimeout(refreshTimerRef.current);
            refreshTimerRef.current = null;
        }
    }, []);

    /** Exchange the httpOnly refresh cookie for a new access token */
    const refreshSession = useCallback(async (): Promise<boolean> => {
        try {
            const { data } = await api.post('/auth/refresh');
            const { access_token, user: refreshedUser } = data;
            setToken(access_token);
            setUser(refreshedUser);
            setApiToken(access_token);      // update axios interceptor
            
            // Schedule next refresh
            const expiry = getTokenExpiry(access_token);
            if (expiry) {
                clearRefreshTimer();
                const delay = expiry - Date.now() - REFRESH_BUFFER_MS;
                if (delay > 0) {
                    refreshTimerRef.current = setTimeout(() => refreshSession(), delay);
                } else {
                    refreshSession();
                }
            }
            
            return true;
        } catch {
            // Refresh token expired or invalid — force logout
            setToken(null);
            setUser(null);
            setApiToken(null);              // clear axios interceptor
            clearRefreshTimer();
            return false;
        }
    }, [clearRefreshTimer]);

    /** Called after a successful login/register */
    const login = useCallback((newToken: string, loggedInUser: User) => {
        setToken(newToken);
        setUser(loggedInUser);
        setApiToken(newToken);              // update axios interceptor
        
        const expiry = getTokenExpiry(newToken);
        if (expiry) {
            clearRefreshTimer();
            const delay = expiry - Date.now() - REFRESH_BUFFER_MS;
            if (delay > 0) {
                refreshTimerRef.current = setTimeout(() => refreshSession(), delay);
            }
        }
    }, [refreshSession, clearRefreshTimer]);

    /** Logout: call backend to clear refresh cookie + blacklist access token */
    const logout = useCallback(async () => {
        clearRefreshTimer();
        try {
            if (token) {
                await api.post('/auth/logout');
            }
        } catch {
            // Non-fatal — still clear local state
        } finally {
            setToken(null);
            setUser(null);
            setApiToken(null);              // clear axios interceptor
        }
    }, [token, clearRefreshTimer]);

    const hasRole = useCallback((roles: Role[]): boolean => {
        if (!user) return false;
        return roles.includes(user.role);
    }, [user]);

    const isAdmin = useCallback((): boolean => {
        if (!user) return false;
        return user.role === 'ADMIN1' || user.role === 'SUPERADMIN';
    }, [user]);

    // On mount: attempt to restore session using the httpOnly refresh cookie
    useEffect(() => {
        const initSession = async () => {
            try {
                await refreshSession();
            } finally {
                setIsInitializing(false);
            }
        };
        initSession();

        // Listen for auth:unauthorized events (emitted by api.ts interceptor)
        const handleUnauthorized = () => logout();
        window.addEventListener('auth:unauthorized', handleUnauthorized);
        return () => {
            window.removeEventListener('auth:unauthorized', handleUnauthorized);
            clearRefreshTimer();
        };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    return (
        <AuthContext.Provider
            value={{ 
                user, token, login, logout, 
                isAuthenticated: !!token, hasRole, isAdmin, isInitializing,
                updateProfile
            }}
        >
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
