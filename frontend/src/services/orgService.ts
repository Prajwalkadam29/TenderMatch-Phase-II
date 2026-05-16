import api from './api';

export interface OrgProfile {
    id: string;
    name: string;
    owner_id: string;
    industry?: string;
    description?: string;
    website?: string;
    location?: string;
    is_active: boolean;
    created_at?: string;
}

export interface OrgUpdatePayload {
    name?: string;
    industry?: string;
    description?: string;
    website?: string;
    location?: string;
}

export const getOrgProfile = async (): Promise<OrgProfile> => {
    const res = await api.get<OrgProfile>('/organization/profile');
    return res.data;
};

export const updateOrgProfile = async (data: OrgUpdatePayload): Promise<OrgProfile> => {
    const res = await api.put<OrgProfile>('/organization/profile', data);
    return res.data;
};

export const createOrganization = async (data: { name: string; industry?: string; description?: string }): Promise<OrgProfile> => {
    const res = await api.post<OrgProfile>('/organization/create', data);
    return res.data;
};
