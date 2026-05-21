import api from './api';

// ─── Legacy types (Dashboard) ─────────────────────────────────────────────────

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

// ─── v3.0 types ───────────────────────────────────────────────────────────────

export interface RunMatchRequest {
    vendor_profile_id: string;
    tender_mongo_id: string;
    use_langgraph?: boolean;
}

export interface TaskResponse {
    task_id: string;
    status: string;
}

export type TaskState = 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'queued';

export interface TaskStatusResponse {
    task_id: string;
    status: TaskState;
    result?: MatchDetailFull;
    error?: string;
}

export interface MatchHistoryItem {
    match_id: string;
    vendor_id: string;
    tender_id: string;
    final_score: number;
    recommendation: string;
    created_at: string;
    pipeline: 'langgraph' | 'direct' | string;
}

export interface MatchDetailFull {
    match_id: string;
    vendor_profile_id: string;
    vendor_id: string;
    tender_mongo_id: string;
    matched_at: string;
    pipeline: string;
    semantic_score: number;
    hard_filter_results: {
        overall_pass: boolean;
        disqualification_reason?: string;
        failed_check?: string;
        check_results: Array<{ check: string; passed: boolean; reason?: string }>;
    };
    weighted_score: {
        final_score: number;
        eligibility_status: string;
        breakdown: Record<string, number>;
    };
    explanation: {
        executive_summary: string;
        strengths: string[];
        risk_factors: string[];
        score_rationale: Record<string, string>;
        recommendation: string;
        recommendation_detail: string;
        confidence_note?: string;
    };
    recommendation: string;
    recommendation_detail: string;
}

export interface FeedbackRequest {
    match_id: string;
    signal: 'interested' | 'not_relevant' | 'submitted' | 'won' | 'lost';
}

// ─── Service functions ─────────────────────────────────────────────────────────

export const matchingService = {
    // ── Legacy (Dashboard) ────────────────────────────────────────────────────
    getStatus: async (): Promise<MatchSummary> => {
        const { data } = await api.get('/match/status');
        return data;
    },

    getTopMatches: async (vendorId: string, k: number = 5): Promise<MatchResult[]> => {
        const { data } = await api.get(`/match/${vendorId}?k=${k}`);
        return data.results ?? [];
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
    },

    // ── v3.0 Async Pipeline ───────────────────────────────────────────────────

    /** POST /match/run → returns {task_id, status} immediately */
    runMatch: async (req: RunMatchRequest): Promise<TaskResponse> => {
        const { data } = await api.post('/match/run', req);
        return data;
    },

    /** GET /match/status/{task_id} → poll for task completion */
    getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
        const { data } = await api.get(`/match/status/${taskId}`);
        return data;
    },

    /** GET /match/history → paginated list of past runs for current org */
    getHistory: async (params?: {
        vendor_profile_id?: string;
        limit?: number;
        offset?: number;
    }): Promise<MatchHistoryItem[]> => {
        const { data } = await api.get('/match/history', { params });
        return data;
    },

    /** GET /match/{match_id} → full v3.0 match detail */
    getMatchDetail: async (matchId: string): Promise<MatchDetailFull> => {
        const { data } = await api.get(`/match/${matchId}`);
        return data;
    },

    /** POST /match/feedback → record user signal */
    submitFeedback: async (req: FeedbackRequest): Promise<{ acknowledged: boolean }> => {
        const { data } = await api.post('/match/feedback', req);
        return data;
    },

    /** GET /match/weights/{vendor_profile_id} → fetch learned weights */
    getWeights: async (vendorProfileId: string): Promise<{ status: string, vendor_profile_id: string, weights: Record<string, number> }> => {
        const { data } = await api.get(`/match/weights/${vendorProfileId}`);
        return data;
    },
};
