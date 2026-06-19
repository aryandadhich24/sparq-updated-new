'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { DecisionDetail, ActionType, ConfidenceTier } from '@/lib/types';
import { useParams } from 'next/navigation';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { AppShell } from '@/components/AppShell';
import Link from 'next/link';

const actionBg: Record<ActionType, string> = {
    KILL: 'bg-red-100 text-red-800 border-red-200',
    SCALE: 'bg-green-100 text-green-800 border-green-200',
    MAINTAIN: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    INVESTIGATE: 'bg-orange-100 text-orange-800 border-orange-200',
};

const actionIcon: Record<ActionType, string> = {
    SCALE: '\u2191',
    MAINTAIN: '\u2192',
    INVESTIGATE: '?',
    KILL: '\u2193',
};

const riskColors: Record<string, string> = {
    high: 'bg-red-50 border-red-200 text-red-800',
    medium: 'bg-amber-50 border-amber-200 text-amber-800',
    low: 'bg-green-50 border-green-200 text-green-800',
};

const tierConfig: Record<ConfidenceTier, { bg: string; label: string; tooltip: string }> = {
    DIRECT: {
        bg: 'bg-green-100 text-green-800 border-green-300',
        label: 'Direct',
        tooltip: 'Outcome directly linked to this decision',
    },
    HIGH: {
        bg: 'bg-blue-100 text-blue-800 border-blue-300',
        label: 'High',
        tooltip: 'Strong source and contextual match',
    },
    MODERATE: {
        bg: 'bg-amber-100 text-amber-800 border-amber-300',
        label: 'Moderate',
        tooltip: 'Partial signal match — review recommended',
    },
    LOW: {
        bg: 'bg-gray-100 text-gray-600 border-gray-300',
        label: 'Low',
        tooltip: 'Based on timing only — treat as estimate',
    },
};

const signalConfig: Record<ConfidenceTier, { dot: string; label: string }> = {
    DIRECT: { dot: 'bg-green-500', label: 'Direct link' },
    HIGH: { dot: 'bg-blue-500', label: 'Source match' },
    MODERATE: { dot: 'bg-amber-500', label: 'Contextual' },
    LOW: { dot: 'bg-gray-400', label: 'Estimated' },
};

function DecisionTierBadge({ tier }: { tier: ConfidenceTier }) {
    const cfg = tierConfig[tier];
    return (
        <span
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold border ${cfg.bg}`}
            title={cfg.tooltip}
        >
            {tier === 'DIRECT' && (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
            )}
            {cfg.label}
        </span>
    );
}

function SignalTypeBadge({ signalType }: { signalType: ConfidenceTier }) {
    const cfg = signalConfig[signalType];
    return (
        <span className="inline-flex items-center gap-1.5 text-xs text-gray-700" title={tierConfig[signalType].tooltip}>
            <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
            {cfg.label}
        </span>
    );
}

/* ---- Confidence Meter ---- */
function ConfidenceMeter({ confidence }: { confidence: number }) {
    const pct = Math.round(confidence * 100);
    const color = pct >= 70 ? 'text-green-600' : pct >= 50 ? 'text-yellow-600' : 'text-red-500';
    const trackColor = pct >= 70 ? 'stroke-green-500' : pct >= 50 ? 'stroke-yellow-500' : 'stroke-red-400';
    const label = pct >= 70 ? 'High' : pct >= 50 ? 'Medium' : 'Low';
    const circumference = 2 * Math.PI * 40;
    const dashOffset = circumference - (pct / 100) * circumference;

    return (
        <div className="flex flex-col items-center">
            <div className="relative w-24 h-24">
                <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
                    <circle
                        cx="50" cy="50" r="40"
                        fill="none"
                        className={trackColor}
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={dashOffset}
                        style={{ transition: 'stroke-dashoffset 0.6s ease' }}
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className={`text-xl font-bold ${color}`}>{pct}%</span>
                </div>
            </div>
            <span className={`text-xs font-medium mt-1 ${color}`}>{label} Confidence</span>
        </div>
    );
}

/* ---- Loading Skeleton ---- */
function DetailSkeleton() {
    return (
        <AppShell>
            <main className="p-4 sm:p-8">
                <div className="max-w-5xl mx-auto space-y-6">
                    {/* Back link placeholder */}
                    <div className="h-4 w-32 bg-gray-200 rounded animate-pulse" />
                    {/* Summary card */}
                    <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm animate-pulse space-y-6">
                        <div className="flex justify-between">
                            <div className="space-y-3">
                                <div className="h-5 w-20 bg-gray-200 rounded-full" />
                                <div className="h-8 w-72 bg-gray-200 rounded" />
                                <div className="h-4 w-48 bg-gray-100 rounded" />
                            </div>
                            <div className="h-10 w-24 bg-gray-200 rounded-full" />
                        </div>
                        <div className="border-t pt-6 grid grid-cols-5 gap-6">
                            {Array.from({ length: 5 }).map((_, i) => (
                                <div key={i} className="space-y-2">
                                    <div className="h-3 w-16 bg-gray-200 rounded" />
                                    <div className="h-6 w-24 bg-gray-200 rounded" />
                                </div>
                            ))}
                        </div>
                    </div>
                    {/* Chart placeholder */}
                    <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm animate-pulse">
                        <div className="h-5 w-48 bg-gray-200 rounded mb-4" />
                        <div className="h-72 bg-gray-50 rounded" />
                    </div>
                </div>
            </main>
        </AppShell>
    );
}

export default function DecisionDetailPage() {
    const params = useParams();
    const [decision, setDecision] = useState<DecisionDetail | null>(null);
    const [insight, setInsight] = useState<any>(null);
    const [insightLoading, setInsightLoading] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!params.id) return;
        const id = Number(params.id);

        api.fetchDecisionDetail(id)
            .then(setDecision)
            .catch((e) => console.error(e))
            .finally(() => setLoading(false));
    }, [params.id]);

    const loadInsight = () => {
        if (!params.id || insightLoading) return;
        setInsightLoading(true);
        api.fetchDecisionInsight(Number(params.id))
            .then(setInsight)
            .catch((e) => console.error(e))
            .finally(() => setInsightLoading(false));
    };

    if (loading) return <DetailSkeleton />;
    if (!decision) return (
        <AppShell>
            <div className="p-12 text-center">
                <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center text-3xl mb-4">?</div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">Decision not found</h2>
                <p className="text-gray-500 mb-4">It may have been deleted or the ID is invalid.</p>
                <Link href="/dashboard" className="text-indigo-600 hover:underline text-sm font-medium">Back to Dashboard</Link>
            </div>
        </AppShell>
    );

    const isRecurring = decision.type === 'HIRE' || decision.type === 'TOOL';
    const netReturn = decision.value - decision.total_cost;

    const chartData = decision.related_outcomes.map(o => ({
        date: new Date(o.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        deal_value: o.value,
        attributed: Math.round(o.attributed_amount),
        name: o.description || `Deal #${o.id}`,
    }));

    return (
        <AppShell>
        <main className="p-4 sm:p-8">
            <div className="max-w-5xl mx-auto space-y-6">

                {/* Breadcrumb */}
                <div className="flex items-center gap-2 text-sm">
                    <Link href="/dashboard" className="text-gray-500 hover:text-indigo-600 transition-colors">Dashboard</Link>
                    <span className="text-gray-300">/</span>
                    <span className="text-gray-900 font-medium truncate max-w-xs">{decision.description}</span>
                </div>

                {/* Summary Card */}
                <div className="bg-white p-6 sm:p-8 rounded-xl border border-gray-200 shadow-sm">
                    <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
                        <div className="min-w-0">
                            <span className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded border border-purple-200 mb-2 inline-block">
                                {decision.type.replace('_', ' ')}
                            </span>
                            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{decision.description}</h1>
                            <p className="text-gray-500 mt-1 text-sm">
                                Started {new Date(decision.start_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                                {decision.end_date && (
                                    <> &middot; Ended {new Date(decision.end_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</>
                                )}
                            </p>
                        </div>
                        <div className="flex items-center gap-4 shrink-0">
                            <div className="flex flex-col items-center gap-2">
                                <ConfidenceMeter confidence={decision.confidence} />
                                {decision.confidence_tier && (
                                    <DecisionTierBadge tier={decision.confidence_tier} />
                                )}
                            </div>
                            <div className="text-center">
                                <span className={`inline-flex items-center gap-1 px-4 py-2 rounded-full text-lg font-bold border ${actionBg[decision.action]}`}>
                                    <span>{actionIcon[decision.action]}</span>
                                    {decision.action}
                                </span>
                                <div className="text-xs text-gray-400 uppercase tracking-wide mt-1">Recommendation</div>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 sm:gap-6 mt-8 border-t pt-8">
                        <div>
                            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{isRecurring ? 'Monthly Cost' : 'Cost'}</div>
                            <div className="text-xl font-semibold text-gray-900 mt-1">${decision.cost.toLocaleString()}{isRecurring && '/mo'}</div>
                        </div>
                        <div>
                            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total Invested</div>
                            <div className="text-xl font-semibold text-gray-900 mt-1">${decision.total_cost.toLocaleString()}</div>
                        </div>
                        <div>
                            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Attributed Revenue</div>
                            <div className="text-xl font-semibold text-green-600 mt-1">${decision.value.toLocaleString()}</div>
                        </div>
                        <div>
                            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">ROI Multiple</div>
                            <div className={`text-xl font-bold mt-1 ${
                                decision.roi >= 3 ? 'text-green-600' : decision.roi < 1 ? 'text-red-600' : 'text-gray-900'
                            }`}>
                                {decision.roi.toFixed(2)}x
                            </div>
                        </div>
                        <div>
                            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Net Return</div>
                            <div className={`text-xl font-semibold mt-1 ${netReturn >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {netReturn >= 0 ? '+' : ''}${Math.abs(netReturn).toLocaleString()}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Attribution Explanation */}
                <div className="bg-white p-6 sm:p-8 rounded-xl border border-gray-200 shadow-sm">
                    <h2 className="text-lg font-bold text-gray-900 mb-3">Attribution Analysis</h2>
                    <p className="text-gray-700 leading-relaxed">
                        {decision.explanation}
                    </p>
                </div>

                {/* Attribution Quality Guide */}
                {decision.confidence_tier && (
                    <div className="bg-gray-50 p-5 rounded-xl border border-gray-200 shadow-sm">
                        <div className="flex items-center gap-2 mb-3">
                            <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                            </svg>
                            <h3 className="text-sm font-semibold text-gray-700">Attribution Quality</h3>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-green-500 shrink-0" />
                                <span><span className="font-medium text-gray-700">Direct</span> <span className="text-gray-500">-- outcome linked to decision</span></span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
                                <span><span className="font-medium text-gray-700">High</span> <span className="text-gray-500">-- strong source match</span></span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
                                <span><span className="font-medium text-gray-700">Moderate</span> <span className="text-gray-500">-- partial signal</span></span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-gray-400 shrink-0" />
                                <span><span className="font-medium text-gray-700">Low</span> <span className="text-gray-500">-- timing only</span></span>
                            </div>
                        </div>
                    </div>
                )}

                {/* AI Deep Analysis Panel */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                    <div className="p-6 border-b border-gray-100 flex items-center justify-between">
                        <div>
                            <h2 className="text-lg font-bold text-gray-900">AI Decision Intelligence</h2>
                            <p className="text-sm text-gray-500 mt-0.5">Benchmarks, risk signals, and data-backed recommendations</p>
                        </div>
                        {!insight && (
                            <button
                                onClick={loadInsight}
                                disabled={insightLoading}
                                className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 disabled:opacity-50 text-sm font-medium"
                            >
                                {insightLoading ? 'Analyzing...' : 'Run AI Analysis'}
                            </button>
                        )}
                    </div>

                    {insightLoading && (
                        <div className="p-8 text-center text-gray-400">
                            <div className="animate-pulse">Analyzing decision against historical patterns...</div>
                        </div>
                    )}

                    {insight && (
                        <div className="p-6 space-y-6">
                            {/* Main Analysis */}
                            <div className="bg-gray-50 rounded-lg p-5">
                                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">Analysis</h3>
                                <p className="text-gray-800 leading-relaxed">{insight.analysis}</p>
                            </div>

                            {/* Benchmarks */}
                            {insight.benchmarks?.has_benchmarks && (
                                <div>
                                    <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                                        Peer Benchmarks ({insight.benchmarks.peer_count} similar {insight.benchmarks.decision_type} decisions)
                                    </h3>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <div className="bg-gray-50 rounded-lg p-4 text-center">
                                            <div className="text-2xl font-bold text-purple-600">{insight.benchmarks.percentile_rank}th</div>
                                            <div className="text-xs text-gray-500 mt-1">Percentile Rank</div>
                                        </div>
                                        <div className="bg-gray-50 rounded-lg p-4 text-center">
                                            <div className="text-2xl font-bold">{insight.benchmarks.avg_roi}x</div>
                                            <div className="text-xs text-gray-500 mt-1">Avg ROI (this type)</div>
                                        </div>
                                        <div className="bg-gray-50 rounded-lg p-4 text-center">
                                            <div className="text-2xl font-bold text-green-600">{insight.benchmarks.top_quartile_roi}x</div>
                                            <div className="text-xs text-gray-500 mt-1">Top Quartile ROI</div>
                                        </div>
                                        <div className="bg-gray-50 rounded-lg p-4 text-center">
                                            <div className="text-2xl font-bold">${insight.benchmarks.avg_attributed_value?.toLocaleString()}</div>
                                            <div className="text-xs text-gray-500 mt-1">Avg Attributed Value</div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Risk & Opportunities */}
                            {insight.risk_assessment && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {/* Risks */}
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                                            Risk Score: <span className={
                                                insight.risk_assessment.risk_score === 'high' ? 'text-red-600' :
                                                insight.risk_assessment.risk_score === 'medium' ? 'text-amber-600' : 'text-green-600'
                                            }>{insight.risk_assessment.risk_score.toUpperCase()}</span>
                                        </h3>
                                        {insight.risk_assessment.risks.length > 0 ? (
                                            <div className="space-y-2">
                                                {insight.risk_assessment.risks.map((r: any, i: number) => (
                                                    <div key={i} className={`p-3 rounded-md border text-sm ${riskColors[r.severity]}`}>
                                                        <span className="font-medium uppercase text-xs">{r.severity}</span>
                                                        <span className="mx-1.5">·</span>
                                                        {r.message}
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <div className="p-3 rounded-md border bg-green-50 border-green-200 text-green-800 text-sm">
                                                No risk signals detected
                                            </div>
                                        )}
                                    </div>

                                    {/* Opportunities */}
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Opportunities</h3>
                                        {insight.risk_assessment.opportunities.length > 0 ? (
                                            <div className="space-y-2">
                                                {insight.risk_assessment.opportunities.map((o: any, i: number) => (
                                                    <div key={i} className="p-3 rounded-md border bg-blue-50 border-blue-200 text-blue-800 text-sm">
                                                        {o.message}
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <div className="p-3 rounded-md border bg-gray-50 border-gray-200 text-gray-500 text-sm">
                                                No standout opportunities identified yet
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Similar Decisions */}
                            {insight.similar_decisions?.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Comparable Decisions</h3>
                                    <div className="space-y-2">
                                        {insight.similar_decisions.map((s: any) => (
                                            <div key={s.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg text-sm">
                                                <div>
                                                    <span className="font-medium text-gray-900">{s.description}</span>
                                                    <span className="text-gray-400 ml-2">${s.total_cost?.toLocaleString()} invested</span>
                                                </div>
                                                <div className="flex items-center gap-4">
                                                    <span className={`font-bold ${s.roi >= 1 ? 'text-green-600' : 'text-red-600'}`}>
                                                        {s.roi}x ROI
                                                    </span>
                                                    <span className={`text-xs px-2 py-0.5 rounded-full border ${actionBg[s.recommendation as ActionType] || 'bg-gray-100'}`}>
                                                        {s.recommendation}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Outcome Patterns */}
                            {insight.outcome_patterns?.has_patterns && (
                                <div>
                                    <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Outcome Patterns</h3>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                        <div className="bg-gray-50 rounded-lg p-3 text-center">
                                            <div className="text-lg font-bold">{insight.outcome_patterns.outcome_count}</div>
                                            <div className="text-xs text-gray-500">Linked Outcomes</div>
                                        </div>
                                        <div className="bg-gray-50 rounded-lg p-3 text-center">
                                            <div className="text-lg font-bold">{insight.outcome_patterns.velocity_per_30d}/mo</div>
                                            <div className="text-xs text-gray-500">Outcome Velocity</div>
                                        </div>
                                        <div className="bg-gray-50 rounded-lg p-3 text-center">
                                            <div className="text-lg font-bold">{insight.outcome_patterns.time_to_first_outcome_days ?? '—'}d</div>
                                            <div className="text-xs text-gray-500">Time to First Outcome</div>
                                        </div>
                                        <div className="bg-gray-50 rounded-lg p-3 text-center">
                                            <div className="text-lg font-bold capitalize">{insight.outcome_patterns.concentration}</div>
                                            <div className="text-xs text-gray-500">Revenue Spread</div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Revenue Attribution Chart */}
                {chartData.length > 0 && (
                    <div className="bg-white p-6 sm:p-8 rounded-xl border border-gray-200 shadow-sm">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-bold text-gray-900">Revenue Attribution by Deal</h2>
                            <div className="flex items-center gap-4 text-xs text-gray-500">
                                <span className="flex items-center gap-1.5">
                                    <span className="inline-block w-3 h-3 rounded-sm bg-gray-200" />
                                    Deal Value
                                </span>
                                <span className="flex items-center gap-1.5">
                                    <span className="inline-block w-3 h-3 rounded-sm bg-purple-500" />
                                    Attributed
                                </span>
                            </div>
                        </div>
                        <div className="h-[300px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                                    <XAxis
                                        dataKey="name"
                                        fontSize={11}
                                        tickMargin={10}
                                        angle={chartData.length > 4 ? -20 : 0}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
                                        fontSize={11}
                                        tickFormatter={(v) => {
                                            if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
                                            if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}k`;
                                            return `$${v}`;
                                        }}
                                        tickLine={false}
                                        axisLine={false}
                                        width={60}
                                    />
                                    <Tooltip
                                        contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '13px' }}
                                        formatter={(value: number, name: string) => [
                                            `$${Number(value).toLocaleString()}`,
                                            name === 'deal_value' ? 'Deal Value' : 'Attributed to This Decision',
                                        ]}
                                    />
                                    <Bar dataKey="deal_value" fill="#e5e7eb" name="deal_value" radius={[4, 4, 0, 0]} />
                                    <Bar dataKey="attributed" fill="#7c3aed" name="attributed" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {/* Outcome Table */}
                {decision.related_outcomes.length > 0 && (
                    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                        <div className="px-6 py-4 border-b flex items-center justify-between">
                            <h2 className="text-lg font-bold text-gray-900">Linked Outcomes</h2>
                            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
                                {decision.related_outcomes.length} deal{decision.related_outcomes.length !== 1 ? 's' : ''}
                            </span>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left text-gray-600">
                                <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b">
                                    <tr>
                                        <th className="px-6 py-3">Deal</th>
                                        <th className="px-6 py-3">Close Date</th>
                                        <th className="px-6 py-3">Signal</th>
                                        <th className="px-6 py-3 text-right">Deal Value</th>
                                        <th className="px-6 py-3 text-right">Attribution Share</th>
                                        <th className="px-6 py-3 text-right">Attributed Amount</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {decision.related_outcomes.map((o) => (
                                        <tr key={o.id} className="bg-white border-b last:border-b-0 hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-3 font-medium text-gray-900">
                                                {o.description || `Outcome #${o.id}`}
                                            </td>
                                            <td className="px-6 py-3 text-gray-500">
                                                {new Date(o.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                            </td>
                                            <td className="px-6 py-3">
                                                {o.signal_type ? (
                                                    <SignalTypeBadge signalType={o.signal_type} />
                                                ) : (
                                                    <span className="text-xs text-gray-400">--</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-3 text-right font-mono text-gray-900">
                                                ${o.value.toLocaleString()}
                                            </td>
                                            <td className="px-6 py-3 text-right">
                                                <div className="inline-flex items-center gap-2">
                                                    <div className="w-12 bg-gray-200 rounded-full h-1.5">
                                                        <div
                                                            className="h-1.5 rounded-full bg-purple-500"
                                                            style={{ width: `${Math.min(o.share * 100, 100)}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-xs text-gray-600">{(o.share * 100).toFixed(1)}%</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-3 text-right font-mono font-medium text-purple-700">
                                                ${o.attributed_amount.toLocaleString()}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        </main>
        </AppShell>
    );
}
