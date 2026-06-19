"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";

export default function SettingsPage() {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [settings, setSettings] = useState<any>({});
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            const org = await api.fetchOrgDetails();
            setSettings(org.settings || {});
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        try {
            await api.updateOrgSettings(settings);
            setMessage("Settings saved successfully.");
            setTimeout(() => setMessage(null), 3000);
        } catch (e) {
            console.error(e);
            setMessage("Failed to save settings.");
        } finally {
            setSaving(false);
        }
    };

    const handleChange = (key: string, value: string) => {
        setSettings({ ...settings, [key]: value });
    };

    return (
        <AppShell>
            <div className="p-8">
                <div className="max-w-4xl mx-auto space-y-8">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
                            <p className="text-sm text-gray-500 mt-1">Manage organization preferences.</p>
                        </div>
                        <Link href="/dashboard" className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                            ← Back to Dashboard
                        </Link>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {/* Sidebar / Navigation for settings could go here, for now just cards */}

                        {/* General Settings */}
                        <div className="md:col-span-2 space-y-6">
                            <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
                                <h2 className="text-lg font-medium text-gray-900 mb-4">General Preferences</h2>
                                {loading ? (
                                    <div className="text-center text-gray-500">Loading settings...</div>
                                ) : (
                                    <form onSubmit={handleSave} className="space-y-6">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                Attribution Lookback Window (Days)
                                            </label>
                                            <p className="text-xs text-gray-500 mb-2">
                                                Outcomes occurring after this many days from the decision start date will not be attributed.
                                            </p>
                                            <input
                                                type="number"
                                                required
                                                min="1"
                                                max="365"
                                                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border text-black"
                                                value={settings.attribution_window || "90"}
                                                onChange={(e) => handleChange("attribution_window", e.target.value)}
                                            />
                                        </div>

                                        <div className="pt-4 border-t border-gray-100 flex justify-end">
                                            <button
                                                type="submit"
                                                disabled={saving}
                                                className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50 transition"
                                            >
                                                {saving ? "Saving..." : "Save Settings"}
                                            </button>
                                        </div>

                                        {message && (
                                            <div className={`mt-4 p-3 rounded-md text-sm ${message.includes("Failed") ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
                                                {message}
                                            </div>
                                        )}
                                    </form>
                                )}
                            </div>
                        </div>

                        {/* Quick Links */}
                        <div className="space-y-6">
                            <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
                                <h2 className="text-lg font-medium text-gray-900 mb-4">Billing & Plans</h2>
                                <p className="text-sm text-gray-500 mb-4">
                                    Manage your subscription, view invoices, and upgrade your plan.
                                </p>
                                <Link
                                    href="/settings/billing"
                                    className="block w-full text-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition"
                                >
                                    Manage Billing
                                </Link>
                            </div>

                            <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
                                <h2 className="text-lg font-medium text-gray-900 mb-4">Team Management</h2>
                                <p className="text-sm text-gray-500 mb-4">
                                    Invite team members and manage roles.
                                </p>
                                <Link
                                    href="/settings/team"
                                    className="block w-full text-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition"
                                >
                                    Manage Team
                                </Link>
                            </div>

                            <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
                                <h2 className="text-lg font-medium text-gray-900 mb-4">Audit Logs</h2>
                                <p className="text-sm text-gray-500 mb-4">
                                    View system activity and security logs.
                                </p>
                                <Link
                                    href="/settings/audit"
                                    className="block w-full text-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition"
                                >
                                    View Logs
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </AppShell>
    );
}
