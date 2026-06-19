'use client';

import { Decision, ActionType, ConfidenceTier } from '@/lib/types';
import Link from 'next/link';

const actionConfig: Record<ActionType, { bg: string; icon: string }> = {
    SCALE: { bg: 'bg-green-100 text-green-800 border-green-200', icon: '\u2191' },
    MAINTAIN: { bg: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: '\u2192' },
    INVESTIGATE: { bg: 'bg-orange-100 text-orange-800 border-orange-200', icon: '?' },
    KILL: { bg: 'bg-red-100 text-red-800 border-red-200', icon: '\u2193' },
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

function ConfidenceTierBadge({ tier, confidence }: { tier?: ConfidenceTier; confidence: number }) {
    if (!tier) {
        // Fallback to old percentage display when tier is not available
        return (
            <div className="flex items-center justify-center gap-2">
                <div className="w-16 bg-gray-200 rounded-full h-1.5">
                    <div
                        className={`h-1.5 rounded-full ${
                            confidence >= 0.7 ? 'bg-green-500' : confidence >= 0.5 ? 'bg-yellow-500' : 'bg-red-400'
                        }`}
                        style={{ width: `${Math.min(confidence * 100, 100)}%` }}
                    />
                </div>
                <span className="text-xs text-gray-500 w-8 text-right">{(confidence * 100).toFixed(0)}%</span>
            </div>
        );
    }

    const cfg = tierConfig[tier];
    return (
        <span
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${cfg.bg}`}
            title={cfg.tooltip}
        >
            {tier === 'DIRECT' && (
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
            )}
            {cfg.label}
        </span>
    );
}

const ActionBadge = ({ action }: { action: ActionType }) => {
    const cfg = actionConfig[action] || actionConfig.MAINTAIN;
    return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border ${cfg.bg}`}>
            <span>{cfg.icon}</span>
            {action}
        </span>
    );
};

const TypeBadge = ({ type }: { type: string }) => {
    const colors: Record<string, string> = {
        'AD_CAMPAIGN': 'bg-blue-50 text-blue-700 border-blue-200',
        'HIRE': 'bg-violet-50 text-violet-700 border-violet-200',
        'TOOL': 'bg-cyan-50 text-cyan-700 border-cyan-200',
        'VENDOR': 'bg-orange-50 text-orange-700 border-orange-200',
    };
    const label = (type || 'UNKNOWN').replace('_', ' ');

    return (
        <span className={`text-xs px-2 py-0.5 rounded border whitespace-nowrap ${colors[type] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
            {label}
        </span>
    );
};

function formatROI(roi: number): { text: string; className: string } {
    const text = `${roi >= 0 ? '+' : ''}${roi.toFixed(2)}x`;
    if (roi >= 3) return { text, className: 'text-green-600' };
    if (roi >= 1) return { text, className: 'text-green-600' };
    if (roi >= 0) return { text, className: 'text-amber-600' };
    return { text, className: 'text-red-600' };
}

export function DecisionTable({ decisions }: { decisions: Decision[] }) {
    if (!decisions.length) {
        return null; // Empty state handled by the dashboard page now
    }

    return (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm bg-white">
            {/* Desktop table */}
            <table className="w-full text-sm text-left text-gray-600 hidden md:table">
                <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b">
                    <tr>
                        <th className="px-6 py-3">Decision</th>
                        <th className="px-6 py-3">Type</th>
                        <th className="px-6 py-3 text-right">Total Cost</th>
                        <th className="px-6 py-3 text-right">Attributed Value</th>
                        <th className="px-6 py-3 text-right">ROI</th>
                        <th className="px-6 py-3 text-center">Confidence</th>
                        <th className="px-6 py-3 text-center">Recommendation</th>
                    </tr>
                </thead>
                <tbody>
                    {decisions.map((d) => {
                        const roi = formatROI(d.roi);
                        return (
                            <tr key={d.id} className="bg-white border-b hover:bg-gray-50 transition-colors">
                                <td className="px-6 py-4">
                                    <Link href={`/decisions/${d.id}`} className="font-medium text-gray-900 hover:text-indigo-600 transition-colors">
                                        {d.description}
                                    </Link>
                                </td>
                                <td className="px-6 py-4">
                                    <TypeBadge type={d.type || d.decision_type || ''} />
                                </td>
                                <td className="px-6 py-4 text-right font-mono text-gray-900">
                                    ${d.total_cost.toLocaleString()}
                                </td>
                                <td className="px-6 py-4 text-right font-mono text-gray-900">
                                    ${d.value.toLocaleString()}
                                </td>
                                <td className={`px-6 py-4 text-right font-bold font-mono ${roi.className}`}>
                                    {roi.text}
                                </td>
                                <td className="px-6 py-4 text-center">
                                    <ConfidenceTierBadge tier={d.confidence_tier} confidence={d.confidence} />
                                </td>
                                <td className="px-6 py-4 text-center">
                                    <ActionBadge action={d.action} />
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>

            {/* Mobile cards */}
            <div className="md:hidden divide-y divide-gray-100">
                {decisions.map((d) => {
                    const roi = formatROI(d.roi);
                    return (
                        <Link key={d.id} href={`/decisions/${d.id}`} className="block p-4 hover:bg-gray-50 transition-colors">
                            <div className="flex items-start justify-between gap-3 mb-2">
                                <div className="min-w-0">
                                    <p className="font-medium text-gray-900 truncate">{d.description}</p>
                                    <TypeBadge type={d.type || d.decision_type || ''} />
                                </div>
                                <ActionBadge action={d.action} />
                            </div>
                            <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
                                <div>
                                    <span className="text-gray-500 block">Cost</span>
                                    <span className="font-mono font-medium text-gray-900">${d.total_cost.toLocaleString()}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500 block">Revenue</span>
                                    <span className="font-mono font-medium text-gray-900">${d.value.toLocaleString()}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500 block">ROI</span>
                                    <span className={`font-mono font-bold ${roi.className}`}>{roi.text}</span>
                                </div>
                            </div>
                        </Link>
                    );
                })}
            </div>
        </div>
    );
}
