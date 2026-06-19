'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { AppShell } from '@/components/AppShell';
import Link from 'next/link';

export default function AuditLogPage() {
    const [logs, setLogs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [total, setTotal] = useState(0);

    useEffect(() => {
        loadLogs(page);
    }, [page]);

    const loadLogs = async (p: number) => {
        setLoading(true);
        try {
            const data = await api.fetchAuditLogs(p);
            // Support both paginated { items, total, pages } and legacy array response
            if (Array.isArray(data)) {
                setLogs(data);
                setTotalPages(1);
                setTotal(data.length);
            } else {
                setLogs(data.items || []);
                setTotalPages(data.pages || 1);
                setTotal(data.total || 0);
            }
        } catch (e) {
            console.error(e);
            setError("Failed to load logs. Ensure you are an Admin.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <AppShell>
        <main className="p-8">
            <div className="max-w-6xl mx-auto">

                <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mb-8">
                    <div className="px-6 py-4 border-b bg-gray-50 flex justify-between items-center">
                        <div>
                            <h1 className="text-xl font-bold text-gray-900">Audit Logs</h1>
                            <p className="text-sm text-gray-500">
                                Track critical actions performed by users.
                                {total > 0 && <span className="ml-2 text-gray-400">({total} total)</span>}
                            </p>
                        </div>
                        <div className="flex gap-4 items-center">
                            <button
                                onClick={() => api.downloadCSV('audit')}
                                className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                            >
                                <svg className="-ml-1 mr-2 h-4 w-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                                Export CSV
                            </button>
                            <button onClick={() => loadLogs(page)} className="text-indigo-600 text-sm font-medium hover:underline">
                                Refresh
                            </button>
                        </div>
                    </div>

                    {error ? (
                        <div className="p-6 text-center text-red-600 bg-red-50">
                            {error}
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left text-gray-600">
                                <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b">
                                    <tr>
                                        <th className="px-6 py-3">Timestamp</th>
                                        <th className="px-6 py-3">User</th>
                                        <th className="px-6 py-3">Action</th>
                                        <th className="px-6 py-3">Resource</th>
                                        <th className="px-6 py-3">ID</th>
                                        <th className="px-6 py-3">Details</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {loading ? (
                                        <tr><td colSpan={6} className="px-6 py-8 text-center">Loading...</td></tr>
                                    ) : logs.length === 0 ? (
                                        <tr><td colSpan={6} className="px-6 py-8 text-center text-gray-400">No logs found.</td></tr>
                                    ) : logs.map((log) => (
                                        <tr key={log.id} className="bg-white border-b hover:bg-gray-50">
                                            <td className="px-6 py-3 whitespace-nowrap text-gray-500">
                                                {new Date(log.timestamp).toLocaleString()}
                                            </td>
                                            <td className="px-6 py-3 font-medium text-gray-900">
                                                {log.user}
                                                <div className="text-xs text-gray-400 font-normal">{log.user_email}</div>
                                            </td>
                                            <td className="px-6 py-3">
                                                <span className={`px-2 py-1 rounded text-xs font-bold ${log.action === 'DELETE' ? 'bg-red-100 text-red-700' :
                                                    log.action === 'CREATE' ? 'bg-green-100 text-green-700' :
                                                        'bg-blue-100 text-blue-700'
                                                    }`}>
                                                    {log.action}
                                                </span>
                                            </td>
                                            <td className="px-6 py-3">{log.resource_type}</td>
                                            <td className="px-6 py-3 font-mono text-xs">{log.resource_id}</td>
                                            <td className="px-6 py-3">
                                                <details className="cursor-pointer">
                                                    <summary className="text-xs text-indigo-600 hover:underline">View JSON</summary>
                                                    <pre className="mt-2 text-xs bg-gray-50 p-2 rounded border overflow-auto max-w-xs">
                                                        {JSON.stringify(log.details, null, 2)}
                                                    </pre>
                                                </details>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="px-6 py-3 border-t bg-gray-50 flex items-center justify-between text-sm text-gray-500">
                            <span>Page {page} of {totalPages}</span>
                            <div className="flex gap-2">
                                <button
                                    disabled={page <= 1}
                                    onClick={() => setPage(p => p - 1)}
                                    className="px-3 py-1 border rounded text-sm disabled:opacity-40 hover:bg-gray-100"
                                >
                                    Previous
                                </button>
                                <button
                                    disabled={page >= totalPages}
                                    onClick={() => setPage(p => p + 1)}
                                    className="px-3 py-1 border rounded text-sm disabled:opacity-40 hover:bg-gray-100"
                                >
                                    Next
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </main>
        </AppShell>
    );
}
