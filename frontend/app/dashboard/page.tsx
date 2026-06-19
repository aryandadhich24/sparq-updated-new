'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import { api } from '@/lib/api';
import { Decision } from '@/lib/types';
import { DecisionTable } from '@/components/DecisionTable';
import { DashboardControls, FilterOptions } from '@/components/DashboardControls';
import { TrendChart } from '@/components/TrendChart';
import { AppShell } from '@/components/AppShell';
import Link from 'next/link';

/* ------------------------------------------------------------------ */
/*  Skeleton helpers                                                   */
/* ------------------------------------------------------------------ */
function StatCardSkeleton() {
    return (
        <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm animate-pulse">
            <div className="h-4 w-24 bg-gray-200 rounded mb-3" />
            <div className="h-7 w-32 bg-gray-200 rounded mb-2" />
            <div className="h-3 w-16 bg-gray-100 rounded" />
        </div>
    );
}

function TableSkeleton() {
    return (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden animate-pulse">
            <div className="bg-gray-50 border-b px-6 py-3 flex gap-8">
                {[120, 60, 80, 80, 50, 60, 80].map((w, i) => (
                    <div key={i} className="h-3 bg-gray-200 rounded" style={{ width: w }} />
                ))}
            </div>
            {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="px-6 py-4 border-b flex gap-8 items-center">
                    <div className="h-4 w-40 bg-gray-100 rounded" />
                    <div className="h-5 w-16 bg-gray-100 rounded-full" />
                    <div className="h-4 w-20 bg-gray-100 rounded ml-auto" />
                    <div className="h-4 w-20 bg-gray-100 rounded" />
                    <div className="h-4 w-14 bg-gray-100 rounded" />
                    <div className="h-4 w-10 bg-gray-100 rounded" />
                    <div className="h-5 w-20 bg-gray-100 rounded-full" />
                </div>
            ))}
        </div>
    );
}

function ChartSkeleton() {
    return (
        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm animate-pulse">
            <div className="h-5 w-48 bg-gray-200 rounded mb-4" />
            <div className="h-72 bg-gray-50 rounded" />
        </div>
    );
}

/* ------------------------------------------------------------------ */
/*  Empty state                                                        */
/* ------------------------------------------------------------------ */
function EmptyState({ onSeed, syncing }: { onSeed: () => void; syncing: boolean }) {
    return (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
            <div className="mx-auto w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center text-3xl mb-4">
                📊
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">No decisions tracked yet</h3>
            <p className="text-gray-500 max-w-md mx-auto mb-6">
                Start by seeding demo data to explore, or sync your CRM to pull in real revenue data.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                    onClick={onSeed}
                    disabled={syncing}
                    className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition"
                >
                    Seed Demo Data
                </button>
                <Link
                    href="/import"
                    className="px-5 py-2.5 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition"
                >
                    Import CSV
                </Link>
                <Link
                    href="/integrations"
                    className="px-5 py-2.5 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition"
                >
                    Connect CRM
                </Link>
            </div>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/*  Stat card with trend indicator                                     */
/* ------------------------------------------------------------------ */
interface StatCardProps {
    label: string;
    value: string;
    subtext?: string;
    trend?: 'up' | 'down' | 'neutral';
    trendLabel?: string;
    valueColor?: string;
}

function StatCard({ label, value, subtext, trend, trendLabel, valueColor = 'text-gray-900' }: StatCardProps) {
    const trendIcon = trend === 'up' ? '\u2191' : trend === 'down' ? '\u2193' : '\u2192';
    const trendColor = trend === 'up' ? 'text-green-600 bg-green-50' : trend === 'down' ? 'text-red-600 bg-red-50' : 'text-gray-500 bg-gray-50';

    return (
        <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm">
            <p className="text-sm font-medium text-gray-500">{label}</p>
            <p className={`text-2xl font-bold mt-1 ${valueColor}`}>{value}</p>
            <div className="flex items-center gap-2 mt-1.5">
                {trend && (
                    <span className={`inline-flex items-center gap-0.5 text-xs font-medium px-1.5 py-0.5 rounded ${trendColor}`}>
                        {trendIcon} {trendLabel}
                    </span>
                )}
                {subtext && <span className="text-xs text-gray-400">{subtext}</span>}
            </div>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/*  Main dashboard                                                     */
/* ------------------------------------------------------------------ */
export default function Home() {
    const [allDecisions, setAllDecisions] = useState<Decision[]>([]);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [filters, setFilters] = useState<FilterOptions>({
        type: 'ALL',
        dateRange: 'ALL',
        sortBy: 'roi',
        order: 'desc',
    });

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.fetchDecisions();
            setAllDecisions(data);
        } catch (e) {
            console.error('Failed to load decisions:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const showMessage = (msg: string) => {
        setMessage(msg);
        setTimeout(() => setMessage(null), 4000);
    };

    const handleSeed = async () => {
        setSyncing(true);
        try {
            const res = await api.seedData();
            showMessage(res.message);
            await loadData();
        } catch (e) {
            console.error(e);
        } finally {
            setSyncing(false);
        }
    };

    const handleSync = async () => {
        setSyncing(true);
        try {
            const res = await api.ingestHubSpot();
            showMessage(res.message);
            await loadData();
        } catch (e) {
            console.error(e);
        } finally {
            setSyncing(false);
        }
    };

    const handleReset = async () => {
        if (!confirm('This will permanently delete all decisions, outcomes, and attributions for your organization. Continue?')) return;
        setSyncing(true);
        try {
            const res = await api.resetData();
            showMessage(res.message);
            await loadData();
        } catch (e) {
            console.error(e);
        } finally {
            setSyncing(false);
        }
    };

    /* ---- Filtering & sorting ---- */
    const decisions = useMemo(() => {
        let filtered = [...allDecisions];

        // Date range filter
        if (filters.dateRange !== 'ALL') {
            const days = parseInt(filters.dateRange, 10);
            const cutoff = new Date();
            cutoff.setDate(cutoff.getDate() - days);
            filtered = filtered.filter((d) => {
                const date = d.start_date ? new Date(d.start_date) : null;
                return date ? date >= cutoff : true;
            });
        }

        // Type filter
        if (filters.type !== 'ALL') {
            filtered = filtered.filter(
                (d) => (d.type || d.decision_type) === filters.type
            );
        }

        // Sorting
        filtered.sort((a, b) => {
            let valA: number, valB: number;
            switch (filters.sortBy) {
                case 'value': valA = a.value; valB = b.value; break;
                case 'cost': valA = a.total_cost; valB = b.total_cost; break;
                case 'date':
                    valA = a.start_date ? new Date(a.start_date).getTime() : 0;
                    valB = b.start_date ? new Date(b.start_date).getTime() : 0;
                    break;
                default: valA = a.roi; valB = b.roi;
            }
            return filters.order === 'desc' ? valB - valA : valA - valB;
        });

        return filtered;
    }, [allDecisions, filters]);

    /* ---- Derived stats ---- */
    const totalCost = decisions.reduce((acc, d) => acc + d.total_cost, 0);
    const totalValue = decisions.reduce((acc, d) => acc + d.value, 0);
    const avgRoi = decisions.length > 0
        ? decisions.reduce((acc, d) => acc + d.roi, 0) / decisions.length
        : 0;
    const actionsNeeded = decisions.filter(d => d.action === 'KILL' || d.action === 'INVESTIGATE').length;
    const netReturn = totalValue - totalCost;
    const scaleCount = decisions.filter(d => d.action === 'SCALE').length;
    const lowConfidenceCount = decisions.filter(d => d.confidence_tier === 'LOW').length;

    return (
        <AppShell>
            <div className="p-4 sm:p-8">
            <div className="max-w-7xl mx-auto space-y-6">

                {/* Header */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">Decision Ledger</h1>
                        <p className="text-sm text-gray-500 mt-1">Multi-touch ROI attribution for every GTM investment.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button
                            onClick={handleSeed}
                            disabled={syncing}
                            className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-md hover:bg-purple-700 disabled:opacity-50 transition"
                        >
                            {syncing ? 'Working...' : 'Seed Demo Data'}
                        </button>
                        <button
                            onClick={handleSync}
                            disabled={syncing}
                            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50 transition"
                        >
                            Sync Revenue
                        </button>
                        <button
                            onClick={handleReset}
                            disabled={syncing}
                            className="px-4 py-2 bg-gray-200 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-300 disabled:opacity-50 transition"
                        >
                            Reset
                        </button>
                    </div>
                </div>

                {/* Toast message */}
                {message && (
                    <div className="bg-indigo-50 border border-indigo-200 text-indigo-800 text-sm px-4 py-3 rounded-lg flex items-center justify-between">
                        <span>{message}</span>
                        <button onClick={() => setMessage(null)} className="ml-4 text-indigo-600 hover:text-indigo-800 font-bold">&times;</button>
                    </div>
                )}

                {/* Loading skeletons */}
                {loading ? (
                    <>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                            {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
                        </div>
                        <ChartSkeleton />
                        <TableSkeleton />
                    </>
                ) : allDecisions.length === 0 ? (
                    /* Empty state */
                    <EmptyState onSeed={handleSeed} syncing={syncing} />
                ) : (
                    <>
                        {/* Stats */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                            <StatCard
                                label="Total Invested"
                                value={`$${totalCost.toLocaleString()}`}
                                subtext={`${decisions.length} decision${decisions.length !== 1 ? 's' : ''}`}
                            />
                            <StatCard
                                label="Attributed Revenue"
                                value={`$${totalValue.toLocaleString()}`}
                                valueColor="text-green-600"
                                trend={netReturn >= 0 ? 'up' : 'down'}
                                trendLabel={`${netReturn >= 0 ? '+' : ''}$${Math.abs(netReturn).toLocaleString()} net`}
                            />
                            <StatCard
                                label="Average ROI"
                                value={`${avgRoi.toFixed(2)}x`}
                                valueColor={avgRoi >= 1 ? 'text-green-600' : 'text-red-600'}
                                trend={avgRoi >= 2 ? 'up' : avgRoi >= 1 ? 'neutral' : 'down'}
                                trendLabel={avgRoi >= 2 ? 'Strong' : avgRoi >= 1 ? 'Healthy' : 'Below target'}
                            />
                            <StatCard
                                label="Actions Needed"
                                value={String(actionsNeeded)}
                                valueColor={actionsNeeded > 0 ? 'text-red-600' : 'text-green-600'}
                                subtext={`${scaleCount} scaling`}
                                trend={actionsNeeded === 0 ? 'up' : 'down'}
                                trendLabel={actionsNeeded === 0 ? 'All clear' : `${actionsNeeded} to review`}
                            />
                        </div>

                        {/* Low confidence banner */}
                        {lowConfidenceCount > 0 && (
                            <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm px-4 py-3 rounded-lg flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <svg className="w-4 h-4 text-amber-500 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                                    </svg>
                                    <span>
                                        {lowConfidenceCount} decision{lowConfidenceCount !== 1 ? 's have' : ' has'} estimated attribution
                                        <span className="hidden sm:inline"> -- connect integrations for better accuracy</span>
                                    </span>
                                </div>
                                <Link href="/integrations" className="text-amber-700 hover:text-amber-900 font-medium text-xs whitespace-nowrap underline underline-offset-2">
                                    Connect
                                </Link>
                            </div>
                        )}

                        {/* Trend Chart */}
                        <TrendChart decisions={decisions} />

                        {/* Filters */}
                        <DashboardControls onChange={setFilters} defaults={filters} />

                        {/* Table or filtered empty state */}
                        {decisions.length === 0 ? (
                            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-12 text-center">
                                <p className="text-gray-500 text-lg">No decisions match your filters.</p>
                                <p className="text-gray-400 text-sm mt-1">Try adjusting the date range or type filter above.</p>
                            </div>
                        ) : (
                            <DecisionTable decisions={decisions} />
                        )}
                    </>
                )}
            </div>
            </div>
        </AppShell>
    );
}
