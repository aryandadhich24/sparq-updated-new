import { Decision, DecisionDetail } from './types';

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const AUTH_LOGOUT_EVENT = "sparqai:force-logout";

function forceLogout(): void {
    if (typeof window === 'undefined') return;
    if (window.location.pathname === '/login' || window.location.pathname === '/register') return;
    localStorage.removeItem('access_token');
    window.dispatchEvent(new Event(AUTH_LOGOUT_EVENT));
}

function getAuthHeaders(): HeadersInit {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

async function handleResponse<T>(res: Response): Promise<T> {
    if (!res.ok) {
        if (res.status === 401) forceLogout();
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        if (Array.isArray(body.detail)) {
            throw new Error(body.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', '));
        }
        throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return res.json();
}

export const api = {

    // -----------------------------------------------------------------------
    // Auth
    // -----------------------------------------------------------------------
    async register(data: {
        email: string; password: string; full_name: string;
        organization_name: string; invite_token?: string;
    }): Promise<any> {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return handleResponse(res);
    },

    // FIX: FastAPI OAuth2PasswordRequestForm requires application/x-www-form-urlencoded
    // URLSearchParams sets this automatically; FormData sends multipart/form-data which breaks it
    async loginWithCredentials(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
        const body = new URLSearchParams();
        body.append('username', email);
        body.append('password', password);
        const res = await fetch(`${API_BASE}/auth/login`, { method: 'POST', body });
        return handleResponse<{ access_token: string; token_type: string }>(res);
    },

    async refreshToken(): Promise<{ access_token: string; token_type: string }> {
        const res = await fetch(`${API_BASE}/auth/refresh`, { method: 'POST', headers: getAuthHeaders() });
        return handleResponse<{ access_token: string; token_type: string }>(res);
    },

    async forgotPassword(email: string): Promise<{ message: string }> {
        const res = await fetch(`${API_BASE}/auth/forgot-password`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email }),
        });
        return handleResponse<{ message: string }>(res);
    },

    async ssoCallback(code: string): Promise<{ access_token: string; token_type: string }> {
        const res = await fetch(`${API_BASE}/auth/sso/callback`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code }),
        });
        return handleResponse<{ access_token: string; token_type: string }>(res);
    },

    // -----------------------------------------------------------------------
    // Decisions
    // -----------------------------------------------------------------------
    async fetchDecisions(): Promise<Decision[]> {
        const res = await fetch(`${API_BASE}/decisions`, { headers: getAuthHeaders() });
        return handleResponse<Decision[]>(res);
    },

    async fetchDecisionDetail(id: number): Promise<DecisionDetail> {
        const res = await fetch(`${API_BASE}/decisions/${id}`, { headers: getAuthHeaders() });
        return handleResponse<DecisionDetail>(res);
    },

    async fetchDecisionInsight(id: number): Promise<any> {
        const res = await fetch(`${API_BASE}/decisions/${id}/insight`, { headers: getAuthHeaders() });
        return handleResponse<any>(res);
    },

    async createDecision(data: any): Promise<any> {
        const res = await fetch(`${API_BASE}/decisions`, {
            method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data),
        });
        return handleResponse(res);
    },

    async updateDecision(id: number, data: any): Promise<any> {
        const res = await fetch(`${API_BASE}/decisions/${id}`, {
            method: 'PUT', headers: getAuthHeaders(), body: JSON.stringify(data),
        });
        return handleResponse(res);
    },

    async deleteDecision(id: number): Promise<any> {
        const res = await fetch(`${API_BASE}/decisions/${id}`, {
            method: 'DELETE', headers: getAuthHeaders(),
        });
        return handleResponse(res);
    },

    // -----------------------------------------------------------------------
    // Outcomes
    // -----------------------------------------------------------------------
    async createOutcome(data: any): Promise<any> {
        const res = await fetch(`${API_BASE}/outcomes`, {
            method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data),
        });
        return handleResponse(res);
    },

    // -----------------------------------------------------------------------
    // Data seeding & reset
    // -----------------------------------------------------------------------
    async seedData(): Promise<{ message: string }> {
        const res = await fetch(`${API_BASE}/seed`, { method: 'POST', headers: getAuthHeaders() });
        return handleResponse<{ message: string }>(res);
    },

    async resetData(): Promise<{ message: string }> {
        const res = await fetch(`${API_BASE}/reset`, { method: 'DELETE', headers: getAuthHeaders() });
        return handleResponse<{ message: string }>(res);
    },

    // -----------------------------------------------------------------------
    // Organisation
    // -----------------------------------------------------------------------
    async fetchOrgDetails(): Promise<{ id: number; name: string; settings: Record<string, any> }> {
        const res = await fetch(`${API_BASE}/organization/`, { headers: getAuthHeaders() });
        return handleResponse<{ id: number; name: string; settings: Record<string, any> }>(res);
    },

    async updateOrgSettings(settings: Record<string, any>): Promise<{ id: number; name: string; settings: Record<string, any> }> {
        const res = await fetch(`${API_BASE}/organization/settings`, {
            method: 'PUT', headers: getAuthHeaders(),
            body: JSON.stringify({ settings }),
        });
        return handleResponse<{ id: number; name: string; settings: Record<string, any> }>(res);
    },

    // -----------------------------------------------------------------------
    // Team
    // -----------------------------------------------------------------------
    async fetchTeam(): Promise<any[]> {
        const res = await fetch(`${API_BASE}/team/`, { headers: getAuthHeaders() });
        return handleResponse<any[]>(res);
    },

    async inviteMember(email: string, role: string): Promise<{ message: string; link: string; token: string }> {
        const res = await fetch(`${API_BASE}/team/invite`, {
            method: 'POST', headers: getAuthHeaders(),
            body: JSON.stringify({ email, role }),
        });
        return handleResponse<{ message: string; link: string; token: string }>(res);
    },

    async removeMember(userId: number): Promise<{ message: string }> {
        const res = await fetch(`${API_BASE}/team/${userId}`, {
            method: 'DELETE', headers: getAuthHeaders(),
        });
        return handleResponse<{ message: string }>(res);
    },

    // -----------------------------------------------------------------------
    // Audit logs
    // -----------------------------------------------------------------------
    async fetchAuditLogs(page: number = 1, perPage: number = 50): Promise<any> {
        const res = await fetch(`${API_BASE}/audit/?page=${page}&per_page=${perPage}`, {
            headers: getAuthHeaders(),
        });
        return handleResponse(res);
    },

    // -----------------------------------------------------------------------
    // Integrations — status, authorize, exchange, sync, disconnect
    // -----------------------------------------------------------------------
    async fetchIntegrationStatus(): Promise<Record<string, { connected: boolean; last_sync: string | null; expires_at: string | null }>> {
        const res = await fetch(`${API_BASE}/integrations/status`, { headers: getAuthHeaders() });
        return handleResponse(res);
    },

    async getAuthUrl(provider: string): Promise<{ url: string }> {
        const slug = provider.toLowerCase().replace(/_/g, '-');
        const res = await fetch(`${API_BASE}/integrations/${slug}/authorize`, { headers: getAuthHeaders() });
        return handleResponse<{ url: string }>(res);
    },

    async getHubSpotAuthUrl(): Promise<{ url: string }> { return api.getAuthUrl('hubspot'); },
    async getSalesforceAuthUrl(): Promise<{ url: string }> { return api.getAuthUrl('salesforce'); },

    async exchangeToken(provider: string, code: string, authToken: string, state?: string): Promise<{ message: string }> {
        const slug = provider.toLowerCase().replace(/_/g, '-');
        const params = new URLSearchParams({ code });
        if (state) params.set('state', state);
        const res = await fetch(`${API_BASE}/integrations/${slug}/exchange?${params}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
        });
        return handleResponse<{ message: string }>(res);
    },

    async exchangeHubSpotCode(code: string, authToken: string, state?: string): Promise<{ message: string }> {
        return api.exchangeToken('hubspot', code, authToken, state);
    },

    async exchangeSalesforceCode(code: string, authToken: string, state?: string): Promise<{ message: string }> {
        return api.exchangeToken('salesforce', code, authToken, state);
    },

    async ingestHubSpot(): Promise<{ created: number; skipped: number; message: string }> {
        const res = await fetch(`${API_BASE}/integrations/hubspot/ingest`, {
            method: 'POST', headers: getAuthHeaders(),
        });
        return handleResponse<{ created: number; skipped: number; message: string }>(res);
    },

    async ingestSalesforce(): Promise<{ created: number; skipped: number; message: string }> {
        const res = await fetch(`${API_BASE}/integrations/salesforce/ingest`, {
            method: 'POST', headers: getAuthHeaders(),
        });
        return handleResponse<{ created: number; skipped: number; message: string }>(res);
    },

    async syncIntegration(provider: string): Promise<{ created: number; skipped: number; message?: string }> {
        const slug = provider.toLowerCase().replace(/_/g, '-');
        const res = await fetch(`${API_BASE}/integrations/${slug}/ingest`, {
            method: 'POST', headers: getAuthHeaders(),
        });
        return handleResponse<{ created: number; skipped: number; message?: string }>(res);
    },

    async syncAdPlatform(provider: string): Promise<{ message: string; created: number; updated: number }> {
        const slug = provider.toLowerCase().replace(/_/g, '-');
        const res = await fetch(`${API_BASE}/ads/${slug}/sync`, {
            method: 'POST', headers: getAuthHeaders(),
        });
        return handleResponse(res);
    },

    async disconnectIntegration(provider: string): Promise<{ message: string }> {
        const slug = provider.toLowerCase().replace(/_/g, '-');
        const res = await fetch(`${API_BASE}/integrations/${slug}/disconnect`, {
            method: 'DELETE', headers: getAuthHeaders(),
        });
        return handleResponse<{ message: string }>(res);
    },

    // -----------------------------------------------------------------------
    // Bulk import (CSV)
    // -----------------------------------------------------------------------
    async bulkImportDecisions(data: any[]): Promise<{ message: string; errors: string[] }> {
        const res = await fetch(`${API_BASE}/import/decisions/bulk`, {
            method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data),
        });
        return handleResponse<{ message: string; errors: string[] }>(res);
    },

    async bulkImportOutcomes(data: any[]): Promise<{ message: string; errors: string[] }> {
        const res = await fetch(`${API_BASE}/import/outcomes/bulk`, {
            method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(data),
        });
        return handleResponse<{ message: string; errors: string[] }>(res);
    },

    // -----------------------------------------------------------------------
    // CSV export / download
    // -----------------------------------------------------------------------
    async downloadCSV(type: 'decisions' | 'audit'): Promise<void> {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
        const res = await fetch(`${API_BASE}/export/${type}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) {
            if (res.status === 401) forceLogout();
            const body = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(body.detail || 'Export failed');
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${type}_export.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    },

    async exportCSV(): Promise<void> {
        return api.downloadCSV('decisions');
    },

    // -----------------------------------------------------------------------
    // Billing
    // -----------------------------------------------------------------------
    async fetchBillingStatus(): Promise<any> {
        const res = await fetch(`${API_BASE}/billing/status`, { headers: getAuthHeaders() });
        return handleResponse(res);
    },

    async fetchBillingPlans(): Promise<any> {
        const res = await fetch(`${API_BASE}/billing/plans`, { headers: getAuthHeaders() });
        return handleResponse(res);
    },

    async createCheckoutSession(planKey: string, billingCycle: string): Promise<{ checkout_url: string }> {
        const res = await fetch(`${API_BASE}/billing/checkout`, {
            method: 'POST', headers: getAuthHeaders(),
            body: JSON.stringify({ plan: planKey, billing_cycle: billingCycle }),
        });
        return handleResponse<{ checkout_url: string }>(res);
    },

    async createPortalSession(): Promise<{ portal_url: string }> {
        const res = await fetch(`${API_BASE}/billing/portal`, {
            method: 'POST', headers: getAuthHeaders(),
        });
        return handleResponse<{ portal_url: string }>(res);
    },

    // -----------------------------------------------------------------------
    // Dashboard
    // -----------------------------------------------------------------------
    async fetchDashboardStats(): Promise<any> {
        const res = await fetch(`${API_BASE}/dashboard/stats`, { headers: getAuthHeaders() });
        return handleResponse(res);
    },
};
