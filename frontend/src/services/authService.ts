import api from './api';

export interface LoginPayload {
    email: string;
    password: string;
}

export interface RegisterPayload {
    name: string;
    email: string;
    password: string;
    role: 'USER' | 'ADMIN1' | 'SUPERADMIN' | 'CUSTOMER_SUPPORT';
    org_name?: string;
    org_industry?: string;
    org_id?: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user: {
        id: string;
        name: string;
        email: string;
        role: string;
        org_id?: string;
        preferences?: Record<string, unknown>;
    };
}

export const loginUser = async (payload: LoginPayload): Promise<AuthResponse> => {
    const res = await api.post<AuthResponse>('/auth/login', payload);
    return res.data;
};

export const registerUser = async (payload: RegisterPayload): Promise<AuthResponse> => {
    const res = await api.post<AuthResponse>('/auth/register', payload);
    return res.data;
};

export const getMe = async () => {
    const res = await api.get('/auth/me');
    return res.data;
};
