import axios from 'axios';

// Routes that are public — errors here should NEVER clear the session.
// The upload and match endpoints don't require auth, so a 4xx/5xx from
// them (e.g. Groq 502, embedding 500) must not boot the user.
const NEVER_LOGOUT_PATHS: string[] = [];

function isPublicPath(url: string | undefined): boolean {
    if (!url) return false;
    // url may be a relative path ('/upload/vendor') or full URL
    // Extract just the path segment to compare
    try {
        const path = url.startsWith('http')
            ? new URL(url).pathname
            : url.split('?')[0];   // strip query string
        return NEVER_LOGOUT_PATHS.some(p => path.startsWith(p));
    } catch {
        return false;
    }
}

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    timeout: 120_000,   // generous default for LLM + embedding calls
});

// ── Request Interceptor — attach JWT wherever present ─────────────────────────
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ── Response Interceptor — auto-logout ONLY on 401 from protected endpoints ───
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Check the request URL from multiple places (config.url can be
            // undefined if the request fails before being sent)
            const requestUrl: string | undefined =
                error.config?.url ??
                error.request?.responseURL ??
                '';

            if (!isPublicPath(requestUrl)) {
                // Genuine auth failure on a protected route — clear session
                localStorage.removeItem('access_token');
                localStorage.removeItem('user');
                window.dispatchEvent(new Event('auth:unauthorized'));
            }
            // For public routes: just reject the promise — the component's
            // catch block will handle the error and show a message, no logout.
        }
        return Promise.reject(error);
    }
);

export default api;
