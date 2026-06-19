"use client";

import { useState, useCallback, useRef } from "react";
import Papa from "papaparse";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SchemaField {
    key: string;
    label: string;
    required: boolean;
    type: "text" | "number" | "date" | "currency" | "percentage";
    aliases: string[]; // common column name variants for auto-mapping
}

interface CSVImporterProps {
    type: "DECISION" | "OUTCOME";
    onImport: (data: any[]) => Promise<{ message: string; errors: string[] }>;
}

interface ValidationResult {
    valid: any[];
    errors: { row: number; field: string; message: string }[];
}

// ---------------------------------------------------------------------------
// Schema definitions with rich aliases for smart auto-mapping
// ---------------------------------------------------------------------------

const DECISION_SCHEMA: SchemaField[] = [
    { key: "description", label: "Description", required: true, type: "text", aliases: ["description", "name", "title", "campaign", "decision", "item", "label", "initiative", "project"] },
    { key: "decision_type", label: "Type", required: true, type: "text", aliases: ["type", "decision_type", "category", "kind", "channel", "decision type"] },
    { key: "start_date", label: "Start Date", required: true, type: "date", aliases: ["start_date", "date", "start", "start date", "created", "created_at", "launch_date", "begin"] },
    { key: "cost", label: "Cost / Amount", required: true, type: "currency", aliases: ["cost", "amount", "spend", "budget", "investment", "price", "value", "total", "usd"] },
    { key: "status", label: "Status", required: false, type: "text", aliases: ["status", "state", "active"] },
    { key: "end_date", label: "End Date", required: false, type: "date", aliases: ["end_date", "end", "end date", "closed", "finish", "expiry"] },
    { key: "notes", label: "Notes", required: false, type: "text", aliases: ["notes", "note", "comments", "description2", "details", "memo"] },
];

const OUTCOME_SCHEMA: SchemaField[] = [
    { key: "description", label: "Description", required: true, type: "text", aliases: ["description", "name", "deal", "opportunity", "title", "client", "account", "label"] },
    { key: "value", label: "Revenue / Value", required: true, type: "currency", aliases: ["value", "amount", "revenue", "arr", "mrr", "deal_value", "deal value", "total", "usd", "price"] },
    { key: "date", label: "Close Date", required: true, type: "date", aliases: ["date", "close_date", "closedate", "closed_date", "close date", "won_date", "created_at"] },
    { key: "metric_name", label: "Metric", required: false, type: "text", aliases: ["metric", "metric_name", "type", "category"] },
    { key: "source", label: "Source", required: false, type: "text", aliases: ["source", "channel", "origin"] },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalize(s: string) {
    return s.toLowerCase().replace(/[\s_\-\.]/g, "");
}

function autoMap(headers: string[], schema: SchemaField[]): Record<string, string> {
    const mapping: Record<string, string> = {};
    for (const field of schema) {
        for (const header of headers) {
            const h = normalize(header);
            if (field.aliases.some(alias => normalize(alias) === h)) {
                mapping[field.key] = header;
                break;
            }
        }
    }
    return mapping;
}

function parseValue(raw: string, type: SchemaField["type"]): number | string {
    if (type === "currency" || type === "number" || type === "percentage") {
        const cleaned = raw.replace(/[$,€£%\s]/g, "");
        return parseFloat(cleaned);
    }
    return raw;
}

function parseDate(raw: string): string | null {
    if (!raw) return null;
    const d = new Date(raw);
    if (!isNaN(d.getTime())) return d.toISOString().slice(0, 10);
    // Try DD/MM/YYYY
    const dmy = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/);
    if (dmy) {
        const [_, dd, mm, yyyy] = dmy;
        const year = yyyy.length === 2 ? `20${yyyy}` : yyyy;
        const d2 = new Date(`${year}-${mm.padStart(2, "0")}-${dd.padStart(2, "0")}`);
        if (!isNaN(d2.getTime())) return d2.toISOString().slice(0, 10);
    }
    return null;
}

function validateRows(rows: any[], mapping: Record<string, string>, schema: SchemaField[], type: "DECISION" | "OUTCOME"): ValidationResult {
    const valid: any[] = [];
    const errors: { row: number; field: string; message: string }[] = [];

    rows.forEach((row, idx) => {
        const rowNum = idx + 1;
        const out: any = {};
        let rowHasError = false;

        for (const field of schema) {
            const csvCol = mapping[field.key];
            const rawVal = csvCol ? row[csvCol] : undefined;
            const strVal = rawVal !== undefined && rawVal !== null ? String(rawVal).trim() : "";

            if (field.required && !strVal) {
                errors.push({ row: rowNum, field: field.label, message: `Missing required field "${field.label}"` });
                rowHasError = true;
                continue;
            }

            if (!strVal) continue; // optional + empty → skip

            if (field.type === "date") {
                const parsed = parseDate(strVal);
                if (!parsed) {
                    errors.push({ row: rowNum, field: field.label, message: `Invalid date "${strVal}" for "${field.label}"` });
                    rowHasError = true;
                    continue;
                }
                out[field.key] = parsed;
            } else if (["currency", "number", "percentage"].includes(field.type)) {
                const num = parseValue(strVal, field.type);
                if (isNaN(num as number)) {
                    errors.push({ row: rowNum, field: field.label, message: `"${strVal}" is not a valid number for "${field.label}"` });
                    rowHasError = true;
                    continue;
                }
                out[field.key] = num;
            } else {
                out[field.key] = strVal;
            }
        }

        // Defaults
        if (!rowHasError) {
            if (type === "DECISION") {
                if (!out.status) out.status = "ACTIVE";
                out.source = "CSV";
            } else {
                if (!out.metric_name) out.metric_name = "REVENUE";
            }
            // Validate decision_type enum
            if (type === "DECISION" && out.decision_type) {
                const VALID_TYPES = ["AD_CAMPAIGN", "HIRE", "TOOL", "VENDOR", "EVENT", "CONTENT", "OTHER"];
                const upper = out.decision_type.toUpperCase().replace(/\s+/g, "_");
                out.decision_type = VALID_TYPES.includes(upper) ? upper : "OTHER";
            }
            if (!rowHasError) valid.push(out);
        }
    });

    return { valid, errors };
}

// ---------------------------------------------------------------------------
// Step indicator
// ---------------------------------------------------------------------------

function Steps({ current }: { current: number }) {
    const steps = ["Upload", "Map Columns", "Preview & Validate", "Import"];
    return (
        <div className="flex items-center justify-between mb-6">
            {steps.map((s, i) => (
                <div key={s} className="flex items-center">
                    <div className={`flex items-center gap-2 ${i < current ? "text-green-600" : i === current ? "text-indigo-600" : "text-gray-400"}`}>
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold border-2 ${
                            i < current ? "bg-green-100 border-green-500 text-green-600" :
                            i === current ? "bg-indigo-100 border-indigo-500 text-indigo-600" :
                            "bg-gray-100 border-gray-300 text-gray-400"
                        }`}>
                            {i < current ? "✓" : i + 1}
                        </div>
                        <span className="text-xs font-medium hidden sm:block">{s}</span>
                    </div>
                    {i < steps.length - 1 && (
                        <div className={`w-8 sm:w-16 h-0.5 mx-2 ${i < current ? "bg-green-400" : "bg-gray-200"}`} />
                    )}
                </div>
            ))}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function CSVImporter({ type, onImport }: CSVImporterProps) {
    const schema = type === "DECISION" ? DECISION_SCHEMA : OUTCOME_SCHEMA;
    const [step, setStep] = useState(0);
    const [file, setFile] = useState<File | null>(null);
    const [allRows, setAllRows] = useState<any[]>([]);
    const [headers, setHeaders] = useState<string[]>([]);
    const [mapping, setMapping] = useState<Record<string, string>>({});
    const [validation, setValidation] = useState<ValidationResult | null>(null);
    const [importing, setImporting] = useState(false);
    const [result, setResult] = useState<{ message: string; errors: string[] } | null>(null);
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const processFile = useCallback((f: File) => {
        setFile(f);
        Papa.parse(f, {
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
                const cols = results.meta.fields || [];
                setHeaders(cols);
                setAllRows(results.data as any[]);
                setMapping(autoMap(cols, schema));
                setStep(1);
            },
        });
    }, [schema]);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) processFile(e.target.files[0]);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        const f = e.dataTransfer.files[0];
        if (f?.name.endsWith(".csv")) processFile(f);
    };

    const handleValidate = () => {
        const result = validateRows(allRows, mapping, schema, type);
        setValidation(result);
        setStep(2);
    };

    const handleImport = async () => {
        if (!validation) return;
        setImporting(true);
        try {
            const res = await onImport(validation.valid);
            const allErrors = [
                ...validation.errors.map(e => `Row ${e.row}: ${e.message}`),
                ...res.errors,
            ];
            setResult({ message: res.message, errors: allErrors });
            setStep(3);
        } catch (e) {
            setResult({ message: "Import failed — check your connection and try again.", errors: [] });
            setStep(3);
        } finally {
            setImporting(false);
        }
    };

    const reset = () => {
        setStep(0); setFile(null); setAllRows([]); setHeaders([]);
        setMapping({}); setValidation(null); setResult(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const previewRows = allRows.slice(0, 5);
    const mappedCount = Object.values(mapping).filter(Boolean).length;
    const requiredMapped = schema.filter(f => f.required).every(f => mapping[f.key]);

    // -------------------------------------------------------------------------
    // Step 3: Result
    // -------------------------------------------------------------------------
    if (step === 3 && result) {
        const successCount = parseInt(result.message.match(/\d+/)?.[0] || "0");
        return (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
                <Steps current={3} />
                <div className="text-center space-y-4">
                    <div className={`w-16 h-16 rounded-full mx-auto flex items-center justify-center ${result.errors.length === 0 ? "bg-green-100" : "bg-yellow-100"}`}>
                        <span className="text-3xl">{result.errors.length === 0 ? "✓" : "⚠"}</span>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900">{result.message}</h3>
                    {result.errors.length > 0 && (
                        <div className="mt-4 text-left bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700 max-h-48 overflow-y-auto">
                            <p className="font-semibold mb-2">{result.errors.length} issue{result.errors.length > 1 ? "s" : ""} found:</p>
                            <ul className="space-y-1 list-disc pl-4">
                                {result.errors.map((err, i) => <li key={i}>{err}</li>)}
                            </ul>
                        </div>
                    )}
                    <button onClick={reset} className="mt-4 px-6 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition">
                        Import Another File
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <Steps current={step} />

            {/* ----------------------------------------------------------------
                Step 0: Upload
            ---------------------------------------------------------------- */}
            {step === 0 && (
                <div
                    onDrop={handleDrop}
                    onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-xl p-16 text-center cursor-pointer transition-colors ${
                        dragOver ? "border-indigo-400 bg-indigo-50" : "border-gray-300 hover:border-indigo-300 hover:bg-gray-50"
                    }`}
                >
                    <input ref={fileInputRef} type="file" accept=".csv" onChange={handleFileChange} className="hidden" />
                    <div className="text-4xl mb-4">📂</div>
                    <p className="text-gray-700 font-medium">Drop your CSV file here</p>
                    <p className="text-sm text-gray-400 mt-1">or click to browse</p>
                    <p className="text-xs text-gray-400 mt-4">Supports any CSV format — columns will be mapped automatically</p>
                </div>
            )}

            {/* ----------------------------------------------------------------
                Step 1: Map columns
            ---------------------------------------------------------------- */}
            {step === 1 && (
                <div className="space-y-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="font-semibold text-gray-900">{file?.name}</p>
                            <p className="text-sm text-gray-500">{allRows.length} rows · {headers.length} columns detected · {mappedCount} auto-mapped</p>
                        </div>
                        <button onClick={reset} className="text-sm text-gray-400 hover:text-red-500 transition">Remove file</button>
                    </div>

                    {/* Preview table */}
                    <div className="overflow-auto rounded-lg border border-gray-200">
                        <table className="min-w-full text-xs">
                            <thead className="bg-gray-50">
                                <tr>{headers.map(h => <th key={h} className="px-3 py-2 text-left font-medium text-gray-600 border-b whitespace-nowrap">{h}</th>)}</tr>
                            </thead>
                            <tbody>
                                {previewRows.map((row, i) => (
                                    <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                                        {headers.map(h => (
                                            <td key={h} className="px-3 py-2 text-gray-700 border-r last:border-0 max-w-[140px] truncate" title={row[h]}>{row[h]}</td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        <div className="bg-gray-50 px-3 py-1.5 text-xs text-gray-400 text-center border-t">
                            Showing first {Math.min(5, allRows.length)} of {allRows.length} rows
                        </div>
                    </div>

                    {/* Column mapping */}
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-3">Map Columns</h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {schema.map(field => {
                                const isMapped = !!mapping[field.key];
                                return (
                                    <div key={field.key}>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            {field.label}
                                            {field.required && <span className="text-red-500 ml-1">*</span>}
                                            <span className="ml-1 text-xs text-gray-400">({field.type})</span>
                                        </label>
                                        <div className="relative">
                                            <select
                                                value={mapping[field.key] || ""}
                                                onChange={e => setMapping({ ...mapping, [field.key]: e.target.value })}
                                                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 ${
                                                    isMapped ? "border-green-400 bg-green-50" : field.required ? "border-orange-300 bg-orange-50" : "border-gray-300"
                                                }`}
                                            >
                                                <option value="">— Not mapped —</option>
                                                {headers.map(h => <option key={h} value={h}>{h}</option>)}
                                            </select>
                                            {isMapped && (
                                                <span className="absolute right-8 top-2.5 text-xs text-green-600">✓</span>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {!requiredMapped && (
                        <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg text-sm text-orange-700">
                            Map all required fields (marked with *) to continue.
                        </div>
                    )}

                    <div className="flex justify-between">
                        <button onClick={reset} className="px-4 py-2 border border-gray-300 text-sm text-gray-600 rounded-lg hover:bg-gray-50 transition">
                            ← Back
                        </button>
                        <button
                            onClick={handleValidate}
                            disabled={!requiredMapped}
                            className="px-6 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-40 transition"
                        >
                            Validate Data →
                        </button>
                    </div>
                </div>
            )}

            {/* ----------------------------------------------------------------
                Step 2: Preview & Validate
            ---------------------------------------------------------------- */}
            {step === 2 && validation && (
                <div className="space-y-5">
                    {/* Summary pills */}
                    <div className="flex flex-wrap gap-3">
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-full text-sm">
                            <div className="w-2 h-2 rounded-full bg-green-500"></div>
                            <span className="font-medium text-green-700">{validation.valid.length} rows ready to import</span>
                        </div>
                        {validation.errors.length > 0 && (
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 border border-red-200 rounded-full text-sm">
                                <div className="w-2 h-2 rounded-full bg-red-500"></div>
                                <span className="font-medium text-red-700">{validation.errors.length} rows with issues (will be skipped)</span>
                            </div>
                        )}
                    </div>

                    {/* Valid preview */}
                    {validation.valid.length > 0 && (
                        <div>
                            <h3 className="font-semibold text-gray-900 mb-2 text-sm">Preview (first 5 valid rows)</h3>
                            <div className="overflow-auto rounded-lg border border-gray-200">
                                <table className="min-w-full text-xs">
                                    <thead className="bg-green-50">
                                        <tr>
                                            {schema.filter(f => validation.valid[0]?.[f.key] !== undefined).map(f => (
                                                <th key={f.key} className="px-3 py-2 text-left font-medium text-green-700 border-b whitespace-nowrap">{f.label}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {validation.valid.slice(0, 5).map((row, i) => (
                                            <tr key={i} className="border-b last:border-0">
                                                {schema.filter(f => row[f.key] !== undefined).map(f => (
                                                    <td key={f.key} className="px-3 py-2 text-gray-700 border-r last:border-0 max-w-[160px] truncate">{String(row[f.key])}</td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Error list */}
                    {validation.errors.length > 0 && (
                        <div>
                            <h3 className="font-semibold text-gray-900 mb-2 text-sm text-red-700">Validation Issues</h3>
                            <div className="bg-red-50 border border-red-200 rounded-lg p-3 max-h-36 overflow-y-auto space-y-1">
                                {validation.errors.map((e, i) => (
                                    <p key={i} className="text-xs text-red-700">Row {e.row}: {e.message}</p>
                                ))}
                            </div>
                        </div>
                    )}

                    {validation.valid.length === 0 && (
                        <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg text-sm text-orange-700">
                            No valid rows found. Go back and fix the column mapping or check your CSV format.
                        </div>
                    )}

                    <div className="flex justify-between pt-2">
                        <button onClick={() => setStep(1)} className="px-4 py-2 border border-gray-300 text-sm text-gray-600 rounded-lg hover:bg-gray-50 transition">
                            ← Edit Mapping
                        </button>
                        <button
                            onClick={handleImport}
                            disabled={importing || validation.valid.length === 0}
                            className="px-6 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-40 transition"
                        >
                            {importing ? "Importing..." : `Import ${validation.valid.length} rows →`}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
