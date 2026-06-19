"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import Link from "next/link";

function BillingContent() {
    const router = useRouter();
    const searchParams = useSearchParams();

    const [status, setStatus] = useState<any>(null);
    const [plans, setPlans] = useState<any>({});
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState(false);
    const [billingCycle, setBillingCycle] = useState<"monthly" | "annual">("monthly");
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        loadData();
        if (searchParams.get("success")) {
            setMessage("Subscription updated successfully!");
        } else if (searchParams.get("canceled")) {
            setMessage("Checkout canceled.");
        }
    }, [searchParams]);

    const loadData = async () => {
        try {
            const [statusRes, plansRes] = await Promise.all([
                api.fetchBillingStatus(),
                api.fetchBillingPlans()
            ]);
            setStatus(statusRes);
            setPlans(plansRes.plans);
        } catch (e) {
            console.error(e);
            setMessage("Failed to load billing data.");
        } finally {
            setLoading(false);
        }
    };

    const handleUpgrade = async (planKey: string) => {
        setProcessing(true);
        try {
            const res = await api.createCheckoutSession(planKey, billingCycle);
            window.location.href = res.checkout_url;
        } catch (e) {
            console.error(e);
            setMessage("Failed to start checkout.");
            setProcessing(false);
        }
    };

    const handleManage = async () => {
        setProcessing(true);
        try {
            const res = await api.createPortalSession();
            window.location.href = res.portal_url;
        } catch (e) {
            console.error(e);
            setMessage("Failed to open billing portal.");
            setProcessing(false);
        }
    };

    if (loading) {
        return (
            <AppShell>
                <div className="p-8 text-center text-gray-500">Loading billing info...</div>
            </AppShell>
        );
    }

    const currentPlanKey = status?.plan || "free";
    const isAnnual = billingCycle === "annual";

    return (
        <AppShell>
            <div className="p-8">
                <div className="max-w-5xl mx-auto space-y-8">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Billing & Subscription</h1>
                            <p className="text-sm text-gray-500 mt-1">Manage your plan and payment methods.</p>
                        </div>
                        <Link href="/settings" className="text-sm text-indigo-600 hover:text-indigo-800">← Back to Settings</Link>
                    </div>
                    {message && (
                        <div className={`p-4 rounded-md ${message.includes("Failed") || message.includes("canceled") ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
                            {message}
                        </div>
                    )}
                    <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-lg font-medium text-gray-900">Current Plan</h2>
                                <p className="text-gray-500 mt-1 capitalize">
                                    {currentPlanKey === "free" ? "Free Tier" : plans[currentPlanKey]?.name || currentPlanKey}
                                    <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${status.plan_status === 'active' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                                        {status.plan_status}
                                    </span>
                                </p>
                                {status.plan_expires_at && (
                                    <p className="text-xs text-gray-400 mt-1">Renews/Expires: {new Date(status.plan_expires_at).toLocaleDateString()}</p>
                                )}
                            </div>
                            <div>
                                {status.stripe_customer_id && (
                                    <button onClick={handleManage} disabled={processing} className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition">
                                        Manage Subscription
                                    </button>
                                )}
                            </div>
                        </div>
                        <div className="mt-6 pt-6 border-t border-gray-100 grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-sm font-medium text-gray-500">Decisions Limit</p>
                                <p className="text-lg font-semibold text-gray-900">{status.limits?.decisions_limit === -1 ? "Unlimited" : status.limits?.decisions_limit || 10} / mo</p>
                            </div>
                            <div>
                                <p className="text-sm font-medium text-gray-500">Users Limit</p>
                                <p className="text-lg font-semibold text-gray-900">{status.limits?.users_limit === -1 ? "Unlimited" : status.limits?.users_limit || 1}</p>
                            </div>
                        </div>
                    </div>
                    <div>
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-bold text-gray-900">Available Plans</h2>
                            <div className="flex items-center bg-gray-100 p-1 rounded-lg">
                                <button onClick={() => setBillingCycle("monthly")} className={`px-3 py-1 text-sm font-medium rounded-md transition ${billingCycle === "monthly" ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-900"}`}>Monthly</button>
                                <button onClick={() => setBillingCycle("annual")} className={`px-3 py-1 text-sm font-medium rounded-md transition ${billingCycle === "annual" ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-900"}`}>Annual <span className="text-xs text-green-600 ml-1">-20%</span></button>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className={`p-6 rounded-xl border ${currentPlanKey === 'free' ? 'border-indigo-600 ring-1 ring-indigo-600 bg-indigo-50' : 'border-gray-200 bg-white'}`}>
                                <h3 className="text-lg font-bold text-gray-900">Free</h3>
                                <p className="text-2xl font-bold text-gray-900 mt-2">$0 <span className="text-sm font-normal text-gray-500">/mo</span></p>
                                <ul className="mt-4 space-y-3 text-sm text-gray-600">
                                    <li>✓ 10 Decisions / month</li>
                                    <li>✓ 1 User</li>
                                    <li>✓ Manual Entry Only</li>
                                </ul>
                                <button disabled className="mt-6 w-full py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-500 bg-gray-50 cursor-not-allowed">
                                    {currentPlanKey === 'free' ? 'Current Plan' : 'Downgrade via Portal'}
                                </button>
                            </div>
                            {["starter", "growth", "enterprise"].map((key) => {
                                const plan = plans[key];
                                if (!plan) return null;
                                const price = isAnnual ? Math.round(plan.price_monthly * 12 * 0.8 / 12) : plan.price_monthly;
                                const isCurrent = currentPlanKey === key;
                                return (
                                    <div key={key} className={`p-6 rounded-xl border ${isCurrent ? 'border-indigo-600 ring-1 ring-indigo-600 bg-indigo-50' : 'border-gray-200 bg-white'}`}>
                                        <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
                                        <p className="text-2xl font-bold text-gray-900 mt-2">${price} <span className="text-sm font-normal text-gray-500">/mo</span></p>
                                        <p className="text-xs text-gray-500 mt-1">{isAnnual ? 'Billed annually' : 'Billed monthly'}</p>
                                        <ul className="mt-4 space-y-3 text-sm text-gray-600">
                                            <li>✓ {plan.decisions_limit === -1 ? "Unlimited" : plan.decisions_limit} Decisions / month</li>
                                            <li>✓ {plan.users_limit === -1 ? "Unlimited" : plan.users_limit} Users</li>
                                            <li>✓ {plan.integrations.join(", ")}</li>
                                        </ul>
                                        {isCurrent ? (
                                            <button disabled className="mt-6 w-full py-2 px-4 border border-indigo-600 rounded-md text-sm font-medium text-indigo-600 bg-indigo-50">Current Plan</button>
                                        ) : (
                                            <button onClick={() => handleUpgrade(key)} disabled={processing} className="mt-6 w-full py-2 px-4 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 transition">Upgrade</button>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>
        </AppShell>
    );
}

export default function BillingPage() {
    return (
        <Suspense>
            <BillingContent />
        </Suspense>
    );
}
