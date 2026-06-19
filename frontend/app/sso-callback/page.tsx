"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import { api } from "@/lib/api";

function SSOCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { login } = useAuth();
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const code = searchParams.get("code");
        if (!code) {
            setError("No SSO code provided.");
            return;
        }
        api.ssoCallback(code)
            .then((data) => { login(data.access_token); })
            .catch((err) => {
                console.error("SSO Login failed:", err);
                setError("SSO Login failed. Please try again.");
                setTimeout(() => router.push("/login"), 3000);
            });
    }, [searchParams, login, router]);

    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-50">
            <div className="text-center">
                {error ? (
                    <div className="text-red-600 font-medium">
                        <p>{error}</p>
                        <p className="text-sm text-gray-500 mt-2">Redirecting to login...</p>
                    </div>
                ) : (
                    <div className="text-indigo-600">
                        <svg className="animate-spin h-10 w-10 mx-auto mb-4" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <p>Completing secure sign-in...</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function SSOCallbackPage() {
    return (
        <Suspense>
            <SSOCallbackContent />
        </Suspense>
    );
}
