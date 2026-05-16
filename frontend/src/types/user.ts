export type Role = 'USER' | 'ADMIN1' | 'SUPERADMIN' | 'CUSTOMER_SUPPORT';

export interface User {
    id: string;
    name: string;
    email: string;
    role: Role;
    org_id?: string;
    preferences?: Record<string, unknown>;
}

