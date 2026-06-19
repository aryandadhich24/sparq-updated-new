'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { api } from '@/lib/api';
import { useAuth } from '@/app/context/AuthContext';

type Status = 'loading' | 'success' | 'error' | 'waiting';

function CallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { token, isLoading: authLoading } = useAuth();
    const [status, setStatus] = useState<Status>('waiting');
    const [message, setMessage] = useState('');
    const [provider, setProvider] = useState('');

    useEffect(() => {
        const code = searchParams.get('code');
        const providerParam = searchParams.get('provider') || 'hubspot';
        const state = searchParams.get('state') || '';
        const error = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');

        setProvider(providerParam);

        // OAuth provider returned an error
        if (error) {
            setStatus('error');
            setMessage(errorDescription || `Connection to ${providerParam} was denied or failed.`);
            setTimeout(() => router.push('/integrations'), 4000);
            return;
        }

        if (!code) {
            setStatus('error');
            setMessage('No authorization code received. Please try connecting again.');
            setTimeout(() => router.push('/integrations'), 3000);
            return;
        }

        // Wait for auth context to finish loading before we try the exchange
        if (authLoading) return;

        if (!token) {
            setStatus('error');
            setMessage('You must be logged in to connect integrations.');
            setTimeout(() => router.push('/login'), 2000);
            return;
        }

        async function exchange() {
            setStatus('loading');
            const displayName = providerParam.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
            setMessage(`Connecting ${displayName}...`);

            try {
                await api.exchangeToken(providerParam, code!, token!, state);
                setStatus('success');
                setMessage(`${displayName} connected successfully! Redirecting...`);
                setTimeout(() => router.push('/integrations'), 1800);
            } catch (e: any) {
                console.error('OAuth exchange error:', e);
                setStatus('error');
                setMessage(e.message || 'Connection failed. Please try again.');
                setTimeout(() => router.push('/integrations'), 4000);
            }
        }

        exchange();
    }, [searchParams, token, authLoading, router]);

    const displayProvider = provider.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()) || 'Integration';

    return (
        <div className="bg-white p-10 rounded-2xl shadow-lg text-center max-w-sm w-full">
            {/* Icon */}
            <div className="flex items-center justify-center mb-6">
                {status === 'loading' || status === 'waiting' ? (
                    <div className="w-16 h-16 rounded-full border-4 border-indigo-100 border-t-indigo-600 animate-spin" />
                ) : status === 'success' ? (
                    <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                        <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                ) : (
                    <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
                        <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </div>
                )}
            </div>

            <h2 className="text-xl font-bold text-gray-900 mb-2">
                {status === 'success' ? 'Connected!' : status === 'error' ? 'Connection Failed' : `Connecting ${displayProvider}`}
            </h2>

            <p className="text-gray-500 text-sm">
                {message || 'Finalizing your connection…'}
            </p>

            {status === 'error' && (
                <button
                    onClick={() => router.push('/integrations')}
                    className="mt-6 px-5 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
                >
                    Back to Integrations
                </button>
            )}

            {(status === 'loading' || status === 'success') && (
                <p className="mt-4 text-xs text-gray-400">You'll be redirected automatically.</p>
            )}
        </div>
    );
}

export default function CallbackPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <Suspense fallback={
                <div className="bg-white p-10 rounded-2xl shadow-lg text-center max-w-sm w-full">
                    <div className="flex items-center justify-center mb-6">
                        <div className="w-16 h-16 rounded-full border-4 border-indigo-100 border-t-indigo-600 animate-spin" />
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2">Connecting Integration</h2>
                    <p className="text-gray-500 text-sm">Loading…</p>
                </div>
            }>
                <CallbackContent />
            </Suspense>
        </div>
    );
}
