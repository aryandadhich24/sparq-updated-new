"use client";

import { useState, useCallback } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis,
} from "recharts";
import { useAuth } from "../context/AuthContext";
import { API_BASE } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ChartData {
  id: string;
  type: "line" | "bar" | "pie" | "histogram" | "heatmap";
  title: string;
  x_label?: string;
  y_label?: string;
  data: any[];
  columns?: string[];
}

interface SummaryStats {
  count: number; mean: number; median: number; std: number;
  min: number; max: number; sum: number; q25: number; q75: number;
}

interface AnalysisResult {
  filename: string;
  rows: number;
  columns: number;
  column_names: string[];
  dtypes: Record<string, string>;
  null_counts: Record<string, number>;
  detected: {
    date_column: string | null;
    amount_column: string | null;
    category_column: string | null;
    numeric_columns: string[];
    text_columns: string[];
  };
  summary_stats: Record<string, SummaryStats>;
  charts: ChartData[];
  insights: string[];
  preview: Record<string, any>[];
}

// ─── Colour palette ──────────────────────────────────────────────────────────

const COLORS = [
  "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#3b82f6",
  "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#84cc16",
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function InsightBadge({ text }: { text: string }) {
  const isWarning = text.toLowerCase().includes("warning") || text.toLowerCase().includes("missing");
  return (
    <div className={`flex items-start gap-2 p-3 rounded-lg text-sm ${
      isWarning ? "bg-amber-50 border border-amber-200 text-amber-800"
                : "bg-indigo-50 border border-indigo-200 text-indigo-800"
    }`}>
      <span className="mt-0.5 flex-shrink-0">{isWarning ? "⚠️" : "💡"}</span>
      <span>{text}</span>
    </div>
  );
}

function ChartCard({ chart }: { chart: ChartData }) {
  const fmt = (v: number) =>
    v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M`
    : v >= 1_000 ? `${(v / 1_000).toFixed(1)}K`
    : v?.toFixed ? v.toFixed(1) : String(v);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="font-semibold text-gray-800 mb-4">{chart.title}</h3>

      {chart.type === "line" && (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={chart.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="x" tick={{ fontSize: 11 }} tickFormatter={(v) => v?.slice?.(0, 7) ?? v} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={fmt} />
            <Tooltip formatter={(v: any) => fmt(v)} />
            <Line type="monotone" dataKey="y" stroke="#6366f1" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}

      {chart.type === "bar" && (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chart.data} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={fmt} />
            <YAxis type="category" dataKey="x" tick={{ fontSize: 11 }} width={120} />
            <Tooltip formatter={(v: any) => fmt(v)} />
            <Bar dataKey="y" radius={[0, 4, 4, 0]}>
              {chart.data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {chart.type === "pie" && (
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie data={chart.data} dataKey="value" nameKey="label"
              cx="50%" cy="50%" outerRadius={100} label={({ label, percent }) =>
                `${label} ${(percent * 100).toFixed(0)}%`
              }>
              {chart.data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      )}

      {chart.type === "histogram" && (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chart.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="range" tick={{ fontSize: 10 }} interval={Math.floor(chart.data.length / 6)} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="count" fill="#6366f1" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}

      {chart.type === "heatmap" && chart.columns && (
        <div className="overflow-auto">
          <table className="text-xs border-collapse w-full">
            <thead>
              <tr>
                <th className="p-1 text-gray-400"></th>
                {chart.columns.map((c) => (
                  <th key={c} className="p-1 text-gray-600 font-medium text-center max-w-16 truncate"
                    title={c}>{c.slice(0, 10)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {chart.columns.map((row) => (
                <tr key={row}>
                  <td className="p-1 text-gray-600 font-medium text-right pr-2 max-w-16 truncate"
                    title={row}>{row.slice(0, 10)}</td>
                  {chart.columns!.map((col) => {
                    const cell = chart.data.find((d) => d.x === row && d.y === col);
                    const val = cell?.value ?? 0;
                    const abs = Math.abs(val);
                    const bg = val > 0.7 ? "#4f46e5" : val > 0.4 ? "#818cf8"
                      : val > 0.1 ? "#c7d2fe" : val < -0.4 ? "#ef4444"
                      : val < -0.1 ? "#fca5a5" : "#f9fafb";
                    const color = abs > 0.4 ? "#fff" : "#374151";
                    return (
                      <td key={col} className="p-1 text-center rounded"
                        style={{ backgroundColor: bg, color, minWidth: 40 }}>
                        {val.toFixed(2)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AnalysisPage() {
  const { token } = useAuth();
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [activeTab, setActiveTab] = useState<"charts" | "stats" | "preview">("charts");

  const analyze = async (file: File) => {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("analysis_type", "auto");
      const res = await fetch(`${API_BASE}/analysis/csv`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || "Analysis failed");
      }
      const data: AnalysisResult = await res.json();
      setResult(data);
      setActiveTab("charts");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const onDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) await analyze(file);
  }, [token]);

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) await analyze(file);
  };

  const fmt = (n: number) =>
    n >= 1_000_000 ? `${(n / 1_000_000).toFixed(2)}M`
    : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K`
    : n?.toFixed ? n.toFixed(2) : String(n);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">CSV Analysis</h1>
          <p className="text-gray-500 mt-1">
            Upload any CSV — get instant charts, stats, and insights powered by Python.
          </p>
        </div>

        {/* Upload zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer ${
            dragging ? "border-indigo-400 bg-indigo-50"
            : "border-gray-300 bg-white hover:border-indigo-300 hover:bg-gray-50"
          }`}
          onClick={() => document.getElementById("csv-input")?.click()}
        >
          <input id="csv-input" type="file" accept=".csv" className="hidden" onChange={onFileChange} />
          {loading ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
              <p className="text-indigo-600 font-medium">Analysing your data...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 bg-indigo-100 rounded-xl flex items-center justify-center">
                <svg className="w-7 h-7 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <p className="font-semibold text-gray-700">Drop your CSV here or click to browse</p>
                <p className="text-sm text-gray-400 mt-1">Supports any CSV up to 10 MB</p>
              </div>
              {result && (
                <p className="text-xs text-indigo-500 mt-1">
                  Currently showing: <strong>{result.filename}</strong> — drop a new file to replace
                </p>
              )}
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="mt-8 space-y-6">

            {/* Top stat cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard label="Rows" value={result.rows.toLocaleString()} sub={`${result.columns} columns`} />
              <StatCard label="Numeric Cols" value={String(result.detected.numeric_columns.length)}
                sub={result.detected.amount_column ? `Primary: ${result.detected.amount_column}` : undefined} />
              {result.detected.amount_column && result.summary_stats[result.detected.amount_column] && (
                <>
                  <StatCard
                    label={`Total ${result.detected.amount_column}`}
                    value={fmt(result.summary_stats[result.detected.amount_column].sum)}
                    sub={`mean ${fmt(result.summary_stats[result.detected.amount_column].mean)}`}
                  />
                  <StatCard
                    label={`Max ${result.detected.amount_column}`}
                    value={fmt(result.summary_stats[result.detected.amount_column].max)}
                    sub={`min ${fmt(result.summary_stats[result.detected.amount_column].min)}`}
                  />
                </>
              )}
            </div>

            {/* Insights */}
            {result.insights.length > 0 && (
              <div className="space-y-2">
                <h2 className="font-semibold text-gray-800">Key Insights</h2>
                <div className="grid sm:grid-cols-2 gap-2">
                  {result.insights.map((ins, i) => <InsightBadge key={i} text={ins} />)}
                </div>
              </div>
            )}

            {/* Tabs */}
            <div className="border-b border-gray-200">
              <nav className="flex gap-6">
                {(["charts", "stats", "preview"] as const).map((tab) => (
                  <button key={tab} onClick={() => setActiveTab(tab)}
                    className={`pb-3 text-sm font-medium border-b-2 transition-colors capitalize ${
                      activeTab === tab
                        ? "border-indigo-600 text-indigo-600"
                        : "border-transparent text-gray-500 hover:text-gray-700"
                    }`}>
                    {tab === "charts" ? `📊 Charts (${result.charts.length})`
                     : tab === "stats" ? "📐 Statistics"
                     : `🔍 Preview (${Math.min(10, result.rows)} rows)`}
                  </button>
                ))}
              </nav>
            </div>

            {/* Charts tab */}
            {activeTab === "charts" && (
              <div className="grid lg:grid-cols-2 gap-6">
                {result.charts.length === 0 ? (
                  <div className="col-span-2 text-center text-gray-400 py-12">
                    No charts could be generated. Try a CSV with numeric or date columns.
                  </div>
                ) : (
                  result.charts.map((chart) => <ChartCard key={chart.id} chart={chart} />)
                )}
              </div>
            )}

            {/* Stats tab */}
            {activeTab === "stats" && (
              <div className="space-y-4">
                {Object.entries(result.summary_stats).map(([col, stats]) => (
                  <div key={col} className="bg-white rounded-xl border border-gray-200 p-5">
                    <h3 className="font-semibold text-gray-800 mb-3">{col}</h3>
                    <div className="grid grid-cols-3 sm:grid-cols-5 gap-4">
                      {[
                        ["Count", stats.count.toLocaleString()],
                        ["Sum", fmt(stats.sum)],
                        ["Mean", fmt(stats.mean)],
                        ["Median", fmt(stats.median)],
                        ["Std Dev", fmt(stats.std)],
                        ["Min", fmt(stats.min)],
                        ["Max", fmt(stats.max)],
                        ["Q25", fmt(stats.q25)],
                        ["Q75", fmt(stats.q75)],
                      ].map(([label, val]) => (
                        <div key={label}>
                          <p className="text-xs text-gray-400">{label}</p>
                          <p className="font-semibold text-gray-800 text-sm">{val}</p>
                        </div>
                      ))}
                    </div>
                    {/* Inline mini bar showing distribution */}
                    <div className="mt-3 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-400 rounded-full"
                        style={{ width: `${Math.min(100, (stats.mean / stats.max) * 100)}%` }} />
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Mean is {((stats.mean / stats.max) * 100).toFixed(0)}% of max value
                    </p>
                  </div>
                ))}

                {/* Null counts */}
                {Object.values(result.null_counts).some((v) => v > 0) && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
                    <h3 className="font-semibold text-amber-800 mb-3">Missing Values</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {Object.entries(result.null_counts)
                        .filter(([, v]) => v > 0)
                        .map(([col, count]) => (
                          <div key={col}>
                            <p className="text-xs text-amber-700 truncate" title={col}>{col}</p>
                            <p className="font-semibold text-amber-900">
                              {count} ({((count / result.rows) * 100).toFixed(1)}%)
                            </p>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Preview tab */}
            {activeTab === "preview" && (
              <div className="bg-white rounded-xl border border-gray-200 overflow-auto">
                <table className="text-xs w-full">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50">
                      {result.column_names.map((col) => (
                        <th key={col} className="px-3 py-2.5 text-left font-semibold text-gray-600 whitespace-nowrap">
                          {col}
                          <span className="ml-1 text-gray-400 font-normal">
                            {result.dtypes[col]?.includes("float") || result.dtypes[col]?.includes("int") ? "#"
                             : result.dtypes[col]?.includes("datetime") ? "📅" : "Aa"}
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.preview.map((row, i) => (
                      <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                        {result.column_names.map((col) => (
                          <td key={col} className="px-3 py-2 text-gray-700 whitespace-nowrap max-w-48 truncate"
                            title={String(row[col] ?? "")}>
                            {row[col] === null || row[col] === undefined ? (
                              <span className="text-gray-300 italic">null</span>
                            ) : String(row[col])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
