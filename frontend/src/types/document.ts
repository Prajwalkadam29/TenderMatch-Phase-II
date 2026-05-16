// Types for the document upload pipeline and matching engine responses

export interface StructuredData {
    scope?: string;
    eligibility?: string;
    technical_specs?: string;
    certifications: string[];
    location?: string;
    [key: string]: unknown;
}

export interface UploadedDocument {
    id: string;
    type: 'vendor' | 'tender';
    original_filename: string;
    structured_data: StructuredData;
    keywords: string[];
    search_text: string;
    file_url?: string;
    embedding_id?: number | null;
    created_at: string;
}

export interface TenderSummary {
    scope?: string;
    location?: string;
    certifications: string[];
}

export interface MatchResult {
    tender_id: string;
    tender_filename: string;
    semantic_score: number;   // 0–1
    keyword_score: number;    // 0–1
    final_score: number;      // 0–100
    tender_summary: TenderSummary;
    tender_keywords: string[];
    explanation?: string | null;
}

export interface MatchResponse {
    vendor_id: string;
    total_matches: number;
    results: MatchResult[];
}

export interface IndexStatus {
    faiss_index_size: number;
    total_documents: number;
    total_vendors: number;
    total_tenders: number;
}
