"use client";

import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { Decision } from '@/lib/types';

interface TrendProps {
    decisions: Decision[];
}

function formatCurrency(value: number): string {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}k`;
    return `$${value}`;
}

export function TrendChart({ decisions }: TrendProps) {
    if (decisions.length === 0) return null;

    const sorted = [...decisions].sort((a, b) =>
        new Date(a.start_date || "").getTime() - new Date(b.start_date || "").getTime()
    );

    let runCost = 0;
    let runValue = 0;

    const data = sorted.map((d) => {
        runCost += d.total_cost || 0;
        runValue += d.value || 0;
        const roi = runCost > 0 ? runValue / runCost : 0;
        return {
            date: d.start_date,
            Investment: runCost,
            Revenue: runValue,
            ROI: parseFloat(roi.toFixed(2)),
            name: d.description,
        };
    });

    return (
        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-900">Cumulative ROI Performance</h3>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1.5">
                        <span className="inline-block w-3 h-3 rounded-sm bg-gray-300" />
                        Investment
                    </span>
                    <span className="flex items-center gap-1.5">
                        <span className="inline-block w-3 h-3 rounded-sm bg-green-500" />
                        Revenue
                    </span>
                </div>
            </div>
            <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                        <defs>
                            <linearGradient id="gradRevenue" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#16A34A" stopOpacity={0.15} />
                                <stop offset="95%" stopColor="#16A34A" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="gradInvestment" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#9CA3AF" stopOpacity={0.1} />
                                <stop offset="95%" stopColor="#9CA3AF" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                        <XAxis
                            dataKey="date"
                            tickFormatter={(str) => {
                                const d = new Date(str);
                                return isNaN(d.getTime()) ? str : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
                            }}
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            dy={8}
                        />
                        <YAxis
                            fontSize={11}
                            tickFormatter={formatCurrency}
                            tickLine={false}
                            axisLine={false}
                            width={60}
                        />
                        <Tooltip
                            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '13px' }}
                            formatter={(value: number, name: string) => [
                                `$${value.toLocaleString()}`,
                                name,
                            ]}
                            labelFormatter={(label) => {
                                const d = new Date(label);
                                return isNaN(d.getTime()) ? label : d.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' });
                            }}
                        />
                        <Area
                            type="monotone"
                            dataKey="Investment"
                            stroke="#9CA3AF"
                            strokeWidth={2}
                            fill="url(#gradInvestment)"
                            dot={false}
                        />
                        <Area
                            type="monotone"
                            dataKey="Revenue"
                            stroke="#16A34A"
                            strokeWidth={2}
                            fill="url(#gradRevenue)"
                            dot={{ r: 3, fill: '#16A34A', strokeWidth: 0 }}
                            activeDot={{ r: 5 }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
