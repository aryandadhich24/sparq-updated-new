"use client";

import { useState } from "react";

export interface FilterOptions {
    type: string;
    dateRange: string;
    sortBy: string;
    order: "asc" | "desc";
}

interface DashboardControlsProps {
    onChange: (options: FilterOptions) => void;
    defaults?: Partial<FilterOptions>;
}

const dateRangeOptions = [
    { value: "7", label: "Last 7 days" },
    { value: "30", label: "Last 30 days" },
    { value: "90", label: "Last 90 days" },
    { value: "ALL", label: "All time" },
];

const typeOptions = [
    { value: "ALL", label: "All Types" },
    { value: "HIRE", label: "Hire" },
    { value: "AD_CAMPAIGN", label: "Ad Campaign" },
    { value: "TOOL", label: "Tool" },
    { value: "VENDOR", label: "Vendor" },
];

const selectClass =
    "block w-full rounded-md border border-gray-300 bg-white text-sm text-gray-900 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition";

export function DashboardControls({ onChange, defaults }: DashboardControlsProps) {
    const [filters, setFilters] = useState<FilterOptions>({
        type: defaults?.type ?? "ALL",
        dateRange: defaults?.dateRange ?? "ALL",
        sortBy: defaults?.sortBy ?? "roi",
        order: defaults?.order ?? "desc",
    });

    const handleChange = (key: keyof FilterOptions, value: string) => {
        const newFilters = { ...filters, [key]: value } as FilterOptions;
        setFilters(newFilters);
        onChange(newFilters);
    };

    return (
        <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm flex flex-wrap gap-4 items-end justify-between">
            <div className="flex gap-4 flex-wrap items-end">
                {/* Date Range */}
                <div className="min-w-[140px]">
                    <label className="block text-xs font-medium text-gray-500 mb-1">Date Range</label>
                    <select
                        className={selectClass}
                        value={filters.dateRange}
                        onChange={(e) => handleChange("dateRange", e.target.value)}
                    >
                        {dateRangeOptions.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                    </select>
                </div>

                {/* Type Filter */}
                <div className="min-w-[140px]">
                    <label className="block text-xs font-medium text-gray-500 mb-1">Decision Type</label>
                    <select
                        className={selectClass}
                        value={filters.type}
                        onChange={(e) => handleChange("type", e.target.value)}
                    >
                        {typeOptions.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="flex gap-4 flex-wrap items-end">
                {/* Sort By */}
                <div className="min-w-[150px]">
                    <label className="block text-xs font-medium text-gray-500 mb-1">Sort By</label>
                    <select
                        className={selectClass}
                        value={filters.sortBy}
                        onChange={(e) => handleChange("sortBy", e.target.value)}
                    >
                        <option value="roi">ROI</option>
                        <option value="value">Revenue</option>
                        <option value="cost">Investment</option>
                        <option value="date">Start Date</option>
                    </select>
                </div>

                {/* Order */}
                <div className="min-w-[150px]">
                    <label className="block text-xs font-medium text-gray-500 mb-1">Order</label>
                    <select
                        className={selectClass}
                        value={filters.order}
                        onChange={(e) => handleChange("order", e.target.value)}
                    >
                        <option value="desc">Highest First</option>
                        <option value="asc">Lowest First</option>
                    </select>
                </div>
            </div>
        </div>
    );
}
