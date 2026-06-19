"use client";

import { useState } from "react";
import { CSVImporter } from "@/components/CSVImporter";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

const DECISION_TYPES = ["AD_CAMPAIGN", "HIRE", "TOOL", "VENDOR", "EVENT", "CONTENT", "OTHER"];

export default function ImportPage() {
    const [activeTab, setActiveTab] = useState<"DECISION" | "OUTCOME">("DECISION");

    return (
        <AppShell>
            <main className="p-8">
                <div className="max-w-4xl mx-auto space-y-6">

                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">Bulk Import</h1>
                        <p className="text-sm text-gray-500 mt-1">
                            Upload any CSV — columns are detected automatically and mapped to SparqAI fields.
                        </p>
                    </div>

                    {/* Tabs */}
                    <div className="border-b border-gray-200">
                        <nav className="-mb-px flex space-x-8">
                            {(["DECISION", "OUTCOME"] as const).map(tab => (
                                <button
                                    key={tab}
                                    onClick={() => setActiveTab(tab)}
                                    className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                                        activeTab === tab
                                            ? "border-indigo-500 text-indigo-600"
                                            : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                                    }`}
                                >
                                    {tab === "DECISION" ? "Decisions" : "Outcomes (Revenue)"}
                                </button>
                            ))}
                        </nav>
                    </div>

                    {/* Info card */}
                    <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 text-sm text-indigo-800 space-y-1">
                        {activeTab === "DECISION" ? (
                            <>
                                <p className="font-semibold">Importing Decisions</p>
                                <p>Required columns: <strong>Description, Type, Start Date, Cost</strong>. Any column order or naming works — we'll auto-map common variants.</p>
                                <p className="text-xs text-indigo-600 mt-1">
                                    Valid types: {DECISION_TYPES.join(" · ")}. Unrecognised types are mapped to OTHER.
                                </p>
                            </>
                        ) : (
                            <>
                                <p className="font-semibold">Importing Revenue Outcomes</p>
                                <p>Required columns: <strong>Description, Value, Date</strong>. Currency symbols ($, €, £) and commas in numbers are handled automatically.</p>
                            </>
                        )}
                    </div>

                    <CSVImporter
                        type={activeTab}
                        onImport={activeTab === "DECISION" ? api.bulkImportDecisions : api.bulkImportOutcomes}
                    />

                </div>
            </main>
        </AppShell>
    );
}
