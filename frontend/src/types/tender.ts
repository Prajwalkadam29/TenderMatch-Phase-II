export interface Tender {
    id: string;
    title: string;
    organization: string;
    deadline: string; // ISO Date String
    matchScore: number;
    status: 'Open' | 'Closed' | 'Awarded';
    scope?: string;
    eligibility?: string;
    techRequirements?: string[];
    feedback?: 'Interested' | 'Not Relevant' | 'Submitted' | 'Won' | 'Lost';
}
