"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import { api } from "@/lib/api";
import Link from "next/link";

function RegisterForm() {
    const { login } = useAuth();
    const searchParams = useSearchParams();
    const inviteToken = searchParams.get("invite");

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [fullName, setFullName] = useState("");
    const [orgName, setOrgName] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [passwordStrength, setPasswordStrength] = useState(0);

    const checkPasswordStrength = (pwd: string) => {
        let score = 0;
        if (pwd.length >= 8) score++;
        if (pwd.length >= 12) score++;
        if (/[A-Z]/.test(pwd)) score++;
        if (/[0-9]/.test(pwd)) score++;
        if (/[^A-Za-z0-9]/.test(pwd)) score++;
        setPasswordStrength(score);
    };

    const strengthLabel = ["", "Weak", "Fair", "Good", "Strong", "Very Strong"][passwordStrength];
    const strengthColor = ["", "bg-red-400", "bg-orange-400", "bg-yellow-400", "bg-green-400", "bg-green-600"][passwordStrength];

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (loading) return;

        if (password !== confirmPassword) {
            setError("Passwords do not match.");
            return;
        }
        if (password.length < 8) {
            setError("Password must be at least 8 characters.");
            return;
        }

        setError("");
        setLoading(true);
        try {
            await api.register({
                email,
                password,
                full_name: fullName,
                organization_name: inviteToken ? "invite" : orgName,
                ...(inviteToken ? { invite_token: inviteToken } : {}),
            });
            // Auto-login after registration
            const data = await api.loginWithCredentials(email, password);
            login(data.access_token);
        } catch (err: any) {
            setError(err.message || "Registration failed. Please try again.");
            setLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-50 py-12">
            <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-xl shadow-md">
                {/* Logo / Brand */}
                <div className="text-center">
                    <div className="inline-flex items-center justify-center w-12 h-12 bg-indigo-600 rounded-xl mb-3">
                        <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900">
                        {inviteToken ? "Join Your Team" : "Create your account"}
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">
                        {inviteToken
                            ? "You've been invited — fill in your details below."
                            : "Start your free SparqAI workspace"}
                    </p>
                </div>

                {inviteToken && (
                    <div className="p-3 text-sm text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg">
                        ✉️ You&apos;ve been invited to join an organization.
                    </div>
                )}

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
                        <label className="block text-sm font-medium text-gray-700">Full Name</label>
                        <input
                            type="text"
                            required
                            autoComplete="name"
                            className="w-full px-3 py-2.5 mt-1 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 placeholder-gray-400 transition-shadow"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            placeholder="Jane Smith"
                            disabled={loading}
                        />
                    </div>

                    {!inviteToken && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Organization Name</label>
                            <input
                                type="text"
                                required
                                autoComplete="organization"
                                className="w-full px-3 py-2.5 mt-1 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 placeholder-gray-400 transition-shadow"
                                value={orgName}
                                onChange={(e) => setOrgName(e.target.value)}
                                placeholder="Acme Corp"
                                disabled={loading}
                            />
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-gray-700">Work Email</label>
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
                        <label className="block text-sm font-medium text-gray-700">Password</label>
                        <input
                            type="password"
                            required
                            autoComplete="new-password"
                            minLength={8}
                            className="w-full px-3 py-2.5 mt-1 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 transition-shadow"
                            value={password}
                            onChange={(e) => { setPassword(e.target.value); checkPasswordStrength(e.target.value); }}
                            disabled={loading}
                        />
                        {password && (
                            <div className="mt-1.5 space-y-1">
                                <div className="flex gap-1">
                                    {[1,2,3,4,5].map((i) => (
                                        <div
                                            key={i}
                                            className={`h-1 flex-1 rounded-full transition-colors ${
                                                i <= passwordStrength ? strengthColor : 'bg-gray-200'
                                            }`}
                                        />
                                    ))}
                                </div>
                                <p className="text-xs text-gray-500">{strengthLabel}</p>
                            </div>
                        )}
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">Confirm Password</label>
                        <input
                            type="password"
                            required
                            autoComplete="new-password"
                            className={`w-full px-3 py-2.5 mt-1 border rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 transition-shadow ${
                                confirmPassword && confirmPassword !== password
                                    ? 'border-red-300 bg-red-50'
                                    : 'border-gray-300'
                            }`}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            disabled={loading}
                        />
                        {confirmPassword && confirmPassword !== password && (
                            <p className="mt-1 text-xs text-red-500">Passwords don&apos;t match</p>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={loading || (!!confirmPassword && confirmPassword !== password)}
                        className="w-full py-2.5 text-white bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed font-medium transition-colors mt-2"
                    >
                        {loading ? (
                            <span className="flex items-center justify-center gap-2">
                                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                                </svg>
                                Creating account...
                            </span>
                        ) : (inviteToken ? "Join Team" : "Create Account")}
                    </button>

                    <p className="text-xs text-center text-gray-400">
                        By signing up, you agree to our Terms of Service and Privacy Policy.
                    </p>
                </form>

                <p className="text-sm text-center text-gray-600">
                    Already have an account?{" "}
                    <Link href="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    );
}

export default function RegisterPage() {
    return (
        <Suspense>
            <RegisterForm />
        </Suspense>
    );
}
