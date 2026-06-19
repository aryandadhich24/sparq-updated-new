"use client";

import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "@/lib/api";
import Link from "next/link";

export default function LoginPage() {
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [showForgot, setShowForgot] = useState(false);
    const [forgotEmail, setForgotEmail] = useState("");
    const [forgotSent, setForgotSent] = useState(false);
    const [forgotLoading, setForgotLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (loading) return;
        setError("");
        setLoading(true);
        try {
            const data = await api.loginWithCredentials(email, password);
            login(data.access_token);
        } catch (err: any) {
            setError(err.message || "Invalid email or password. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleForgotPassword = async (e: React.FormEvent) => {
        e.preventDefault();
        if (forgotLoading) return;
        setForgotLoading(true);
        try {
            await api.forgotPassword(forgotEmail);
            setForgotSent(true);
        } catch (err: any) {
            // Always show success to prevent email enumeration
            setForgotSent(true);
        } finally {
            setForgotLoading(false);
        }
    };

    if (showForgot) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-50">
                <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-xl shadow-md">
                    <div>
                        <button
                            onClick={() => { setShowForgot(false); setForgotSent(false); setForgotEmail(""); }}
                            className="text-sm text-indigo-600 hover:text-indigo-500 flex items-center gap-1 mb-4"
                        >
                            ← Back to sign in
                        </button>
                        <h2 className="text-2xl font-bold text-gray-900">Reset your password</h2>
                        <p className="mt-1 text-sm text-gray-500">
                            Enter your email and we'll send you a reset link.
                        </p>
                    </div>
                    {forgotSent ? (
                        <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                            ✓ If that email exists, a reset link is on its way. Check your inbox.
                        </div>
                    ) : (
                        <form onSubmit={handleForgotPassword} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Email address</label>
                                <input
                                    type="email"
                                    required
                                    className="w-full px-3 py-2 mt-1 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
                                    value={forgotEmail}
                                    onChange={(e) => setForgotEmail(e.target.value)}
                                    placeholder="you@example.com"
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={forgotLoading}
                                className="w-full py-2.5 text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed font-medium transition-colors"
                            >
                                {forgotLoading ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                                        </svg>
                                        Sending...
                                    </span>
                                ) : "Send reset link"}
                            </button>
                        </form>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-50">
            <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-xl shadow-md">
                {/* Logo / Brand */}
                <div className="text-center">
                    <div className="inline-flex items-center justify-center w-12 h-12 bg-indigo-600 rounded-xl mb-3">
                        <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900">Sign in to SparqAI</h2>
                    <p className="text-sm text-gray-500 mt-1">ROI Decision Intelligence Platform</p>
                </div>

                {/* Error */}
                {error && (
                    <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
                        <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Email address</label>
                        <input
                            type="email"
                            required
                            autoComplete="email"
                            className="w-full px-3 py-2.5 mt-1 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 placeholder-gray-400 transition-shadow"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="you@company.com"
                            disabled={loading}
                        />
                    </div>
                    <div>
                        <div className="flex items-center justify-between">
                            <label className="block text-sm font-medium text-gray-700">Password</label>
                            <button
                                type="button"
                                onClick={() => setShowForgot(true)}
                                className="text-xs text-indigo-600 hover:text-indigo-500"
                            >
                                Forgot password?
                            </button>
                        </div>
                        <input
                            type="password"
                            required
                            autoComplete="current-password"
                            className="w-full px-3 py-2.5 mt-1 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 transition-shadow"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            disabled={loading}
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-2.5 text-white bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed font-medium transition-colors"
                    >
                        {loading ? (
                            <span className="flex items-center justify-center gap-2">
                                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                                </svg>
                                Signing in...
                            </span>
                        ) : "Sign In"}
                    </button>
                </form>

                <p className="text-sm text-center text-gray-600">
                    Don&apos;t have an account?{" "}
                    <Link href="/register" className="font-medium text-indigo-600 hover:text-indigo-500">
                        Create one for free
                    </Link>
                </p>
            </div>
        </div>
    );
}
