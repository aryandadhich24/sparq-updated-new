'use client';

import { useEffect, useState } from 'react';
import { api, API_BASE } from '@/lib/api';
import { useAuth } from '@/app/context/AuthContext';
import { AppShell } from '@/components/AppShell';
import Link from 'next/link';

interface IntegrationDef {
    id: string;
    provider: string;
    name: string;
    description: string;
    icon: React.ReactNode;
    category: 'CRM' | 'Advertising' | 'Finance' | 'HR';
    syncType: 'crm' | 'ads' | 'finance' | 'none';
}

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

function HubSpotIcon({ size = 8 }: { size?: number }) {
    return (
        <svg viewBox="0 0 24 24" className={`w-${size} h-${size}`} fill="none">
            <circle cx="12" cy="12" r="11" fill="#FF7A59" />
            <path d="M14.5 8.5V6.8a1.2 1.2 0 10-1.2 0v1.7a2.8 2.8 0 00-1.5 1.1L9.4 8.1a1.1 1.1 0 10-.5.9l2.3 1.5a2.8 2.8 0 100 2.9L8.9 15a1.1 1.1 0 10.5.9l2.4-1.5a2.8 2.8 0 004.7-2.1 2.8 2.8 0 00-2-2.8z" fill="white" />
        </svg>
    );
}

function SalesforceIcon({ size = 8 }: { size?: number }) {
    return (
        <svg viewBox="0 0 24 24" className={`w-${size} h-${size}`} fill="none">
            <circle cx="12" cy="12" r="11" fill="#00A1E0" />
            <path d="M7 13.5a2.5 2.5 0 014-2 3 3 0 015.5.5 2 2 0 01-.5 4H8a2.5 2.5 0 01-1-4z" fill="white" />
        </svg>
    );
}

function GoogleAdsIcon() {
    return (
        <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none">
            <circle cx="12" cy="12" r="11" fill="#4285F4" />
            <path d="M8 16l4-8 4 8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="8" cy="16" r="1.5" fill="#FBBC04" />
        </svg>
    );
}

function QuickBooksIcon() {
    return (
        <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none">
            <circle cx="12" cy="12" r="11" fill="#2CA01C" />
            <path d="M9 8v8m3-8v8m3-6v4" stroke="white" strokeWidth="2" strokeLinecap="round" />
        </svg>
    );
}

function GenericIcon({ letter, color }: { letter: string; color: string }) {
    return (
        <div className="w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm" style={{ backgroundColor: color }}>
            {letter}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Integration definitions
// ---------------------------------------------------------------------------

const INTEGRATIONS: IntegrationDef[] = [
    { id: 'hubspot', provider: 'hubspot', name: 'HubSpot', description: 'Sync closed-won deals and pipeline data.', icon: <HubSpotIcon />, category: 'CRM', syncType: 'crm' },
    { id: 'salesforce', provider: 'salesforce', name: 'Salesforce', description: 'Import Closed Won opportunities and revenue data.', icon: <SalesforceIcon />, category: 'CRM', syncType: 'crm' },
    { id: 'google_ads', provider: 'google_ads', name: 'Google Ads', description: 'Track campaign spend, conversions, and ROAS.', icon: <GoogleAdsIcon />, category: 'Advertising', syncType: 'ads' },
    { id: 'linkedin_ads', provider: 'linkedin_ads', name: 'LinkedIn Ads', description: 'B2B campaign performance and lead generation.', icon: <GenericIcon letter="Li" color="#0A66C2" />, category: 'Advertising', syncType: 'ads' },
    { id: 'meta_ads', provider: 'meta_ads', name: 'Meta Ads', description: 'Facebook and Instagram advertising data.', icon: <GenericIcon letter="M" color="#1877F2" />, category: 'Advertising', syncType: 'ads' },
    { id: 'quickbooks', provider: 'quickbooks', name: 'QuickBooks', description: 'Vendor payments, tool subscriptions, and expenses.', icon: <QuickBooksIcon />, category: 'Finance', syncType: 'finance' },
    { id: 'xero', provider: 'xero', name: 'Xero', description: 'Accounting data, invoices, and expense tracking.', icon: <GenericIcon letter="X" color="#13B5EA" />, category: 'Finance', syncType: 'none' },
    { id: 'bamboohr', provider: 'bamboohr', name: 'BambooHR', description: 'New hires, compensation, and headcount data.', icon: <GenericIcon letter="B" color="#73C41D" />, category: 'HR', syncType: 'none' },
    { id: 'workday', provider: 'workday', name: 'Workday', description: 'Enterprise HR, payroll, and workforce planning.', icon: <GenericIcon letter="W" color="#F68D2E" />, category: 'HR', syncType: 'none' },
    { id: 'stripe', provider: 'stripe', name: 'Stripe', description: 'Payment data, MRR, churn, and subscription revenue.', icon: <GenericIcon letter="S" color="#635BFF" />, category: 'Finance', syncType: 'none' },
    { id: 'google_analytics', provider: 'google_analytics', name: 'Google Analytics', description: 'Website traffic, conversions, and attribution paths.', icon: <GenericIcon letter="GA" color="#E37400" />, category: 'Advertising', syncType: 'none' },
    { id: 'slack', provider: 'slack', name: 'Slack', description: 'Get AI attribution alerts and weekly digest in Slack.', icon: <GenericIcon letter="S" color="#4A154B" />, category: 'CRM', syncType: 'none' },
];

const ACTIVE_PROVIDERS = new Set(['hubspot', 'salesforce', 'google_ads', 'linkedin_ads', 'meta_ads', 'quickbooks']);

const CATEGORY_META: Record<string, { title: string; description: string }> = {
    CRM: { title: 'CRM & Revenue', description: 'Connect your CRM to auto-import closed deals as revenue outcomes.' },
    Advertising: { title: 'Advertising', description: 'Track ad spend and tie campaigns directly to revenue.' },
    Finance: { title: 'Finance', description: 'Connect accounting tools to track vendor and tool costs.' },
    HR: { title: 'HR & People', description: 'Track hiring decisions and their downstream revenue impact.' },
};

// ---------------------------------------------------------------------------
// HubSpot Modal — matches screenshots exactly
// ---------------------------------------------------------------------------

function HubSpotModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
    const { token } = useAuth();
    const [step, setStep] = useState<1 | 2>(1);
    const [hsToken, setHsToken] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const handleSave = async () => {
        if (!hsToken.trim()) return;
        setSaving(true);
        setError('');
        try {
            const res = await fetch(`${API_BASE}/integrations/hubspot/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ access_token: hsToken.trim() }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed to save credentials');
            onSaved();
            onClose();
        } catch (e: any) {
            setError(e.message);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="flex items-start justify-between p-6 pb-4">
                    <div className="flex items-center gap-3">
                        <HubSpotIcon size={10} />
                        <div>
                            <h2 className="font-bold text-gray-900 text-lg">Connect HubSpot</h2>
                            <p className="text-sm text-gray-500">Private App token — takes 2 minutes</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none mt-1">×</button>
                </div>

                {/* Tab bar */}
                <div className="mx-6 mb-4 grid grid-cols-2 rounded-lg overflow-hidden border border-gray-200">
                    <button
                        onClick={() => setStep(1)}
                        className={`py-2.5 text-sm font-medium transition-colors ${step === 1 ? 'bg-orange-500 text-white' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}
                    >
                        1. Create Token
                    </button>
                    <button
                        onClick={() => setStep(2)}
                        className={`py-2.5 text-sm font-medium transition-colors ${step === 2 ? 'bg-orange-500 text-white' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}
                    >
                        2. Paste Token
                    </button>
                </div>

                {/* Body */}
                <div className="px-6 pb-6">
                    {step === 1 ? (
                        <div className="space-y-4">
                            <p className="text-sm text-gray-700 font-medium">Follow these steps in your HubSpot account:</p>
                            <div className="space-y-3">
                                {[
                                    { n: 1, title: 'Go to your HubSpot account', sub: 'Click Settings ⚙ in the top navigation bar' },
                                    { n: 2, title: 'Navigate to Private Apps', sub: 'Left sidebar → Integrations → Private Apps' },
                                    { n: 3, title: 'Create a new Private App', sub: 'Click "Create a private app" button' },
                                    { n: 4, title: 'Name it SparqAI', sub: 'Give it any name, e.g. "SparqAI Integration"' },
                                    { n: 5, title: 'Add required scopes', sub: 'Click "Scopes" tab → search and add: crm.objects.deals.read' },
                                    { n: 6, title: 'Create and copy token', sub: 'Click "Create app" → copy the token starting with pat-na2-...' },
                                ].map(item => (
                                    <div key={item.n} className="flex items-start gap-3">
                                        <div className="flex-shrink-0 w-6 h-6 rounded-full border-2 border-orange-400 flex items-center justify-center text-xs font-bold text-orange-500">{item.n}</div>
                                        <div>
                                            <p className="text-sm font-medium text-gray-800">{item.title}</p>
                                            <p className="text-xs text-gray-500">{item.sub}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <a
                                href="https://app.hubspot.com/private-apps"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block w-full py-3 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-lg text-center transition-colors"
                            >
                                Open HubSpot Private Apps →
                            </a>
                            <button
                                onClick={() => setStep(2)}
                                className="block w-full py-3 border border-orange-400 text-orange-500 text-sm font-medium rounded-lg text-center hover:bg-orange-50 transition-colors"
                            >
                                I have my token — Next →
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                    HubSpot Private App Token <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    placeholder="pat-na2-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                                    value={hsToken}
                                    onChange={e => setHsToken(e.target.value)}
                                    className="w-full px-3 py-2.5 border border-blue-400 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-orange-300"
                                    autoFocus
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Token must start with <code className="bg-gray-100 px-1 rounded">pat-</code>. Encrypted before storage — never shared.
                                </p>
                            </div>
                            <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-sm text-orange-700">
                                <span className="font-semibold">Required scope:</span> crm.objects.deals.read — this lets SparqAI read your closed deals to calculate ROI attribution.
                            </div>
                            {error && (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">⚠️ {error}</div>
                            )}
                            <div className="flex gap-3 pt-1">
                                <button
                                    onClick={() => setStep(1)}
                                    className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition"
                                >
                                    ← Back
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={saving || !hsToken.trim()}
                                    className="flex-1 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-semibold disabled:opacity-50 transition-colors"
                                >
                                    {saving ? 'Connecting...' : '✓ Save & Connect HubSpot'}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Salesforce Modal — matches screenshots exactly
// ---------------------------------------------------------------------------

function SalesforceModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
    const { token } = useAuth();
    const [step, setStep] = useState<1 | 2>(1);
    const [sfUser, setSfUser] = useState('');
    const [sfPass, setSfPass] = useState('');
    const [sfSecToken, setSfSecToken] = useState('');
    const [sfDomain, setSfDomain] = useState('login');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const canSave = !!(sfUser && sfPass && sfSecToken);

    const handleSave = async () => {
        if (!canSave) return;
        setSaving(true);
        setError('');
        try {
            const res = await fetch(`${API_BASE}/integrations/salesforce/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify({ username: sfUser, password: sfPass, security_token: sfSecToken, domain: sfDomain }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed to save credentials');
            onSaved();
            onClose();
        } catch (e: any) {
            setError(e.message);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="flex items-start justify-between p-6 pb-4">
                    <div className="flex items-center gap-3">
                        <SalesforceIcon size={10} />
                        <div>
                            <h2 className="font-bold text-gray-900 text-lg">Connect Salesforce</h2>
                            <p className="text-sm text-gray-500">Username + Security Token — no OAuth app needed</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none mt-1">×</button>
                </div>

                {/* Tab bar */}
                <div className="mx-6 mb-4 grid grid-cols-2 rounded-lg overflow-hidden border border-gray-200">
                    <button
                        onClick={() => setStep(1)}
                        className={`py-2.5 text-sm font-medium transition-colors ${step === 1 ? 'bg-blue-500 text-white' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}
                    >
                        1. Get Security Token
                    </button>
                    <button
                        onClick={() => setStep(2)}
                        className={`py-2.5 text-sm font-medium transition-colors ${step === 2 ? 'bg-blue-500 text-white' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}
                    >
                        2. Enter Credentials
                    </button>
                </div>

                {/* Body */}
                <div className="px-6 pb-6">
                    {step === 1 ? (
                        <div className="space-y-4">
                            <p className="text-sm text-gray-700 font-medium">Get your Salesforce security token:</p>
                            <div className="space-y-3">
                                {[
                                    { n: 1, title: 'Log in to Salesforce', sub: 'Go to login.salesforce.com' },
                                    { n: 2, title: 'Open your profile', sub: 'Click your avatar/name in the top-right corner' },
                                    { n: 3, title: 'Go to Settings', sub: 'Click "Settings" in the dropdown menu' },
                                    { n: 4, title: 'Find Reset Security Token', sub: 'In the left sidebar search box, type "Reset"' },
                                    { n: 5, title: 'Reset your token', sub: 'Click "Reset My Security Token" → click the button' },
                                    { n: 6, title: 'Check your email', sub: 'Salesforce emails the token within 1 minute' },
                                ].map(item => (
                                    <div key={item.n} className="flex items-start gap-3">
                                        <div className="flex-shrink-0 w-6 h-6 rounded-full border-2 border-blue-400 flex items-center justify-center text-xs font-bold text-blue-500">{item.n}</div>
                                        <div>
                                            <p className="text-sm font-medium text-gray-800">{item.title}</p>
                                            <p className="text-xs text-gray-500">{item.sub}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <a
                                href="https://login.salesforce.com"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block w-full py-3 bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold rounded-lg text-center transition-colors"
                            >
                                Open Salesforce →
                            </a>
                            <button
                                onClick={() => setStep(2)}
                                className="block w-full py-3 border border-blue-400 text-blue-500 text-sm font-medium rounded-lg text-center hover:bg-blue-50 transition-colors"
                            >
                                I have my token — Next →
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                    Username (email) <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="email"
                                    placeholder="you@company.com"
                                    value={sfUser}
                                    onChange={e => setSfUser(e.target.value)}
                                    className="w-full px-3 py-2.5 border border-blue-400 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                                    autoFocus
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                    Password <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="password"
                                    placeholder="Your Salesforce password"
                                    value={sfPass}
                                    onChange={e => setSfPass(e.target.value)}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                    Security Token <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="password"
                                    placeholder="From the email Salesforce sent you"
                                    value={sfSecToken}
                                    onChange={e => setSfSecToken(e.target.value)}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-300"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1.5">Domain</label>
                                <input
                                    type="text"
                                    placeholder="Production (login.salesforce.com)"
                                    value={sfDomain === 'login' ? '' : sfDomain}
                                    onChange={e => setSfDomain(e.target.value || 'login')}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                                />
                            </div>
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
                                All credentials are encrypted with AES-256 before being stored. Never shared or logged.
                            </div>
                            {error && (
                                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">⚠️ {error}</div>
                            )}
                            <div className="flex gap-3 pt-1">
                                <button
                                    onClick={() => setStep(1)}
                                    className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition"
                                >
                                    ← Back
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={saving || !canSave}
                                    className="flex-1 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-semibold disabled:opacity-50 transition-colors"
                                >
                                    {saving ? 'Connecting...' : '✓ Save & Connect Salesforce'}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function IntegrationsPage() {
    const { token } = useAuth();
    const [statuses, setStatuses] = useState<Record<string, any>>({});
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState<string | null>(null);
    const [disconnecting, setDisconnecting] = useState<string | null>(null);
    const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
    const [activeModal, setActiveModal] = useState<'hubspot' | 'salesforce' | null>(null);

    useEffect(() => { loadStatuses(); }, []);

    const loadStatuses = async () => {
        try {
            const data = await api.fetchIntegrationStatus();
            setStatuses(data);
        } catch (e) {
            console.error('Failed to load integration statuses', e);
        } finally {
            setLoading(false);
        }
    };

    const showMessage = (text: string, type: 'success' | 'error') => {
        setMessage({ text, type });
        setTimeout(() => setMessage(null), 5000);
    };

    const handleConnect = async (def: IntegrationDef) => {
        // HubSpot and Salesforce use our paste-flow modal, not OAuth
        if (def.provider === 'hubspot') { setActiveModal('hubspot'); return; }
        if (def.provider === 'salesforce') { setActiveModal('salesforce'); return; }
        try {
            const data = await api.getAuthUrl(def.provider);
            window.location.href = data.url;
        } catch (e) {
            showMessage(`Failed to start ${def.name} connection`, 'error');
        }
    };

    const handleSync = async (def: IntegrationDef) => {
        setSyncing(def.id);
        try {
            if (def.provider === 'hubspot') {
                const res = await api.ingestHubSpot();
                showMessage(`Synced ${res.created} deals from HubSpot`, 'success');
            } else if (def.provider === 'salesforce') {
                const res = await api.ingestSalesforce();
                showMessage(`Salesforce: ${res.created} created, ${res.skipped} skipped`, 'success');
            } else if (def.syncType === 'ads') {
                const res = await api.syncIntegration(def.provider);
                showMessage(`${def.name}: ${res.created} created, ${res.skipped} skipped`, 'success');
            } else if (def.syncType === 'finance') {
                const res = await fetch(`${API_BASE}/quickbooks/sync`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('access_token') : ''}` },
                });
                const data = await res.json();
                showMessage(`QuickBooks: ${data.created} created, ${data.updated} updated`, 'success');
            }
            await loadStatuses();
        } catch (e: any) {
            showMessage(`${def.name} sync failed: ${e.message || 'Unknown error'}`, 'error');
        } finally {
            setSyncing(null);
        }
    };

    const handleDisconnect = async (def: IntegrationDef) => {
        if (!confirm(`Disconnect ${def.name}? Stored credentials will be removed. Your existing data will not be deleted.`)) return;
        setDisconnecting(def.id);
        try {
            await api.disconnectIntegration(def.provider);
            showMessage(`${def.name} disconnected`, 'success');
            await loadStatuses();
        } catch (e: any) {
            showMessage(`Failed to disconnect ${def.name}: ${e.message || 'Unknown error'}`, 'error');
        } finally {
            setDisconnecting(null);
        }
    };

    const categories = ['CRM', 'Advertising', 'Finance', 'HR'];
    const connectedCount = Object.values(statuses).filter((s: any) => s?.connected).length;
    const comingSoonCount = INTEGRATIONS.filter(i => !ACTIVE_PROVIDERS.has(i.id)).length;

    const connectButtonStyle = (provider: string) => {
        if (provider === 'hubspot') return 'w-full py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition';
        if (provider === 'salesforce') return 'w-full py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition';
        return 'w-full py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition';
    };

    return (
        <AppShell>
            {activeModal === 'hubspot' && (
                <HubSpotModal
                    onClose={() => setActiveModal(null)}
                    onSaved={() => {
                        loadStatuses();
                        showMessage('HubSpot connected! Click Sync Now to import your deals.', 'success');
                    }}
                />
            )}
            {activeModal === 'salesforce' && (
                <SalesforceModal
                    onClose={() => setActiveModal(null)}
                    onSaved={() => {
                        loadStatuses();
                        showMessage('Salesforce connected! Click Sync Now to import your opportunities.', 'success');
                    }}
                />
            )}

            <main className="p-8">
                <div className="max-w-6xl mx-auto space-y-8">

                    {/* Header */}
                    <div className="flex justify-between items-start">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Data Integrations</h1>
                            <p className="text-sm text-gray-500 mt-1">
                                Connect your tools to automatically import decisions and outcomes.
                            </p>
                        </div>
                        <Link
                            href="/import"
                            className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition whitespace-nowrap"
                        >
                            Manual CSV Import
                        </Link>
                    </div>

                    {/* Toast */}
                    {message && (
                        <div className={`px-4 py-3 rounded-lg text-sm border ${
                            message.type === 'success'
                                ? 'bg-green-50 border-green-200 text-green-800'
                                : 'bg-red-50 border-red-200 text-red-800'
                        }`}>
                            {message.text}
                        </div>
                    )}

                    {/* Stats bar */}
                    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 flex items-center gap-8">
                        <div className="flex items-center gap-2">
                            <div className="w-2.5 h-2.5 rounded-full bg-green-500"></div>
                            <span className="text-sm text-gray-600">
                                <span className="font-semibold text-gray-900">{connectedCount}</span> connected
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-2.5 h-2.5 rounded-full bg-gray-300"></div>
                            <span className="text-sm text-gray-600">
                                <span className="font-semibold text-gray-900">{comingSoonCount}</span> coming soon
                            </span>
                        </div>
                        <div className="ml-auto text-xs text-gray-400">
                            Synced data triggers attribution recalculation automatically
                        </div>
                    </div>

                    {loading ? (
                        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-12 text-center text-gray-400">
                            Loading integrations...
                        </div>
                    ) : (
                        categories.map((cat) => {
                            const meta = CATEGORY_META[cat];
                            const items = INTEGRATIONS.filter(i => i.category === cat);
                            if (items.length === 0) return null;

                            return (
                                <div key={cat} className="space-y-4">
                                    <div>
                                        <h2 className="text-lg font-semibold text-gray-900">{meta.title}</h2>
                                        <p className="text-sm text-gray-500">{meta.description}</p>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {items.map((def) => {
                                            const isActive = ACTIVE_PROVIDERS.has(def.id);
                                            const status = statuses[def.id];
                                            const isConnected = status?.connected === true;

                                            return (
                                                <div
                                                    key={def.id}
                                                    className={`bg-white rounded-xl border shadow-sm p-5 flex flex-col gap-4 ${
                                                        !isActive ? 'border-gray-100 opacity-70' : 'border-gray-200'
                                                    }`}
                                                >
                                                    {/* Top row */}
                                                    <div className="flex items-start justify-between">
                                                        <div className="flex items-center gap-3">
                                                            {def.icon}
                                                            <div>
                                                                <h3 className="font-semibold text-gray-900">{def.name}</h3>
                                                                {isConnected && (
                                                                    <div className="flex items-center gap-1 mt-0.5">
                                                                        <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>
                                                                        <span className="text-xs text-green-600 font-medium">Connected</span>
                                                                    </div>
                                                                )}
                                                                {!isActive && (
                                                                    <span className="text-xs text-gray-400 font-medium">Coming Soon</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                        {isConnected && (
                                                            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">Active</span>
                                                        )}
                                                    </div>

                                                    {/* Description */}
                                                    <p className="text-sm text-gray-500 leading-relaxed">{def.description}</p>

                                                    {/* Last sync */}
                                                    {isConnected && status?.last_sync && (
                                                        <p className="text-xs text-gray-400">
                                                            Last synced: {new Date(status.last_sync).toLocaleString()}
                                                        </p>
                                                    )}

                                                    {/* Actions */}
                                                    <div className="mt-auto">
                                                        {!isActive ? (
                                                            <button disabled className="w-full py-2 text-sm font-medium text-gray-400 bg-gray-50 rounded-lg cursor-not-allowed border border-gray-100">
                                                                Coming Soon
                                                            </button>
                                                        ) : isConnected ? (
                                                            <div className="flex gap-2">
                                                                <button
                                                                    onClick={() => handleSync(def)}
                                                                    disabled={syncing === def.id}
                                                                    className="flex-1 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition disabled:opacity-50"
                                                                >
                                                                    {syncing === def.id ? 'Syncing...' : 'Sync Now'}
                                                                </button>
                                                                <button
                                                                    onClick={() => handleDisconnect(def)}
                                                                    disabled={disconnecting === def.id}
                                                                    className="py-2 px-3 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition disabled:opacity-50"
                                                                >
                                                                    {disconnecting === def.id ? '...' : 'Disconnect'}
                                                                </button>
                                                            </div>
                                                        ) : (
                                                            <button
                                                                onClick={() => handleConnect(def)}
                                                                className={connectButtonStyle(def.provider)}
                                                            >
                                                                Connect {def.name}
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })
                    )}

                    {/* Custom Integrations */}
                    <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-200 p-6">
                        <div className="flex items-start justify-between">
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900">Custom Integrations</h3>
                                <p className="text-sm text-gray-600 mt-1">
                                    Need to connect a tool not listed here? Use our REST API or webhook endpoint
                                    to push decision and outcome data from any source.
                                </p>
                                <div className="mt-3 flex items-center gap-3">
                                    <code className="text-xs bg-white px-3 py-1.5 rounded border border-indigo-200 text-indigo-700 font-mono">
                                        POST /api/v1/decisions
                                    </code>
                                    <code className="text-xs bg-white px-3 py-1.5 rounded border border-indigo-200 text-indigo-700 font-mono">
                                        POST /api/v1/outcomes
                                    </code>
                                </div>
                            </div>
                            <a
                                href="/api/v1/docs"
                                target="_blank"
                                className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 transition whitespace-nowrap"
                            >
                                API Docs
                            </a>
                        </div>
                    </div>

                </div>
            </main>
        </AppShell>
    );
}
