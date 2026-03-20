// documentService.ts
// API calls for upload pipeline + matching engine

import api from './api';
import type { UploadedDocument, MatchResponse, IndexStatus } from '../types/document';

// ─── Upload ──────────────────────────────────────────────────────────────────

export async function uploadVendor(file: File): Promise<UploadedDocument> {
    const form = new FormData();
    form.append('file', file);
    // ⚠️  Do NOT set Content-Type manually here.
    // When you pass FormData, axios lets the browser set Content-Type automatically,
    // which includes the required multipart boundary string.
    // Setting it manually strips the boundary → FastAPI returns 422.
    const { data } = await api.post<UploadedDocument>('/upload/vendor', form, {
        timeout: 120_000,   // Groq LLM + embedding can take ~30s
    });
    return data;
}

export async function uploadTender(file: File): Promise<UploadedDocument> {
    const form = new FormData();
    form.append('file', file);
    const { data } = await api.post<UploadedDocument>('/upload/tender', form, {
        timeout: 120_000,
    });
    return data;
}

export async function getMyDocuments(type?: string): Promise<UploadedDocument[]> {
    const params = type ? { doc_type: type } : {};
    const { data } = await api.get<UploadedDocument[]>('/upload/my-documents', { params });
    return data;
}

// ─── Matching ─────────────────────────────────────────────────────────────────

export async function matchVendor(
    vendorId: string,
    k = 10,
    explain = false,
): Promise<MatchResponse> {
    const { data } = await api.get<MatchResponse>(`/match/${vendorId}`, {
        params: { k, explain },
        timeout: 120_000,
    });
    return data;
}

export async function getIndexStatus(): Promise<IndexStatus> {
    const { data } = await api.get<IndexStatus>('/match/status');
    return data;
}

