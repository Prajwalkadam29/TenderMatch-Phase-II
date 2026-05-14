import api from './api';

export interface ActivityLog {
    id: string;
    action: string;
    description: string;
    created_at: string;
    actor_name: string;
    status: string;
}

export interface MatchSummary {
    total_documents: number;
    total_vendors: number;
    total_tenders: number;
}

export interface MatchResult {
    eligible: boolean;
    final_score: number;
    tender_id: string;
    tender_filename: string;
    explanation?: string;
    match_result: {
        tender_summary: {
            scope?: string;
            location?: string;
            certifications: string[];
        };
    };
}

export const matchingService = {
    getStatus: async (): Promise<MatchSummary> => {
        const { data } = await api.get('/match/status');
        return data;
    },

    getTopMatches: async (vendorId: string, k: number = 5): Promise<MatchResult[]> => {
        const { data } = await api.get(`/match/${vendorId}?k=${k}`);
        return data.results;
    },

    getOrgActivity: async (limit: number = 10): Promise<ActivityLog[]> => {
        const { data } = await api.get(`/activity/organization?limit=${limit}`);
        return data;
    },

    getDashboardSummary: async (): Promise<{
        total_tenders: number;
        total_documents: number;
        total_profiles: number;
        recent_activity: ActivityLog[];
        profile_completeness: number;
        top_matches_count: number;
    }> => {
        const { data } = await api.get('/activity/summary');
        return data;
    }
};
