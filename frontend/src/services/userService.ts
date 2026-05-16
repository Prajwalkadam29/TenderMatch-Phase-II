import api from './api';

export interface OrgUser {
    id: string;
    name: string;
    email: string;
    role: string;
    org_id?: string;
    is_active: boolean;
    created_at?: string;
}

export interface CreateUserPayload {
    name: string;
    email: string;
    password: string;
    role: 'USER' | 'ADMIN1';
}

export const getOrgUsers = async (): Promise<OrgUser[]> => {
    const res = await api.get<OrgUser[]>('/organization/users');
    return res.data;
};

export const createOrgUser = async (data: CreateUserPayload): Promise<OrgUser> => {
    const res = await api.post<OrgUser>('/organization/users', data);
    return res.data;
};

export const deleteOrgUser = async (userId: string): Promise<void> => {
    await api.delete(`/organization/users/${userId}`);
};
