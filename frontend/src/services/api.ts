/**
 * api.ts
 * ------
 * Axios instance with:
 * - In-memory token attachment (reads from AuthContext, not localStorage)
 * - Automatic token refresh on 401 using the httpOnly refresh cookie
 * - auth:unauthorized event dispatch on unrecoverable 401
 *
 * Token architecture:
 * - Access tokens live ONLY in memory (module-level variable set by AuthContext)
 *   → No localStorage/sessionStorage → XSS-safe
 * - Refresh tokens live in httpOnly cookie set by the server
 *   → JS never touches the refresh token directly
 */

import axios from 'axios';
import type { AxiosRequestConfig } from 'axios';

// ── In-memory token store ─────────────────────────────────────────────────────
// AuthContext calls setApiToken() after login/register/refresh.
// The api interceptor reads it here. Nothing writes to localStorage.

let _accessToken: string | null = null;

export function setApiToken(token: string | null): void {
    _accessToken = token;
}

export function getApiToken(): string | null {
    return _accessToken;
}

// ── Paths that should NOT trigger a logout on 401 ────────────────────────────
// e.g. public search endpoints that use auth optionally
const SKIP_REFRESH_PATHS = ['/auth/login', '/auth/register', '/auth/refresh'];

function isAuthPath(url: string | undefined): boolean {
    if (!url) return false;
    const path = url.startsWith('http') ? new URL(url).pathname : url.split('?')[0];
    return SKIP_REFRESH_PATHS.some(p => path.startsWith(p));
}

// ── Axios instance ────────────────────────────────────────────────────────────

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    timeout: 120_000,   // generous for LLM + embedding calls
    withCredentials: true,  // IMPORTANT: sends httpOnly cookies (refresh token)
});

// ── Request Interceptor — attach in-memory access token ───────────────────────
api.interceptors.request.use(
    (config) => {
        if (_accessToken && config.headers) {
            config.headers.Authorization = `Bearer ${_accessToken}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ── Response Interceptor — refresh on 401 ────────────────────────────────────
let _isRefreshing = false;
let _refreshQueue: Array<(token: string) => void> = [];

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest: AxiosRequestConfig & { _retry?: boolean } = error.config ?? {};

        if (error.response?.status === 401 && !originalRequest._retry && !isAuthPath(originalRequest.url)) {
            if (_isRefreshing) {
                // Queue this request until the ongoing refresh completes
                return new Promise((resolve) => {
                    _refreshQueue.push((newToken: string) => {
                        if (originalRequest.headers) {
                            originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
                        }
                        resolve(api(originalRequest));
                    });
                });
            }

            originalRequest._retry = true;
            _isRefreshing = true;

            try {
                // Use the httpOnly refresh cookie — no manual token needed
                const { data } = await api.post('/auth/refresh');
                const newToken: string = data.access_token;

                _accessToken = newToken;

                // Flush queued requests
                _refreshQueue.forEach(cb => cb(newToken));
                _refreshQueue = [];

                // Retry the original request with the new token
                if (originalRequest.headers) {
                    originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
                }
                return api(originalRequest);
            } catch {
                // Refresh failed — session is gone
                _accessToken = null;
                _refreshQueue = [];
                window.dispatchEvent(new Event('auth:unauthorized'));
                return Promise.reject(error);
            } finally {
                _isRefreshing = false;
            }
        }

        return Promise.reject(error);
    }
);

export default api;
