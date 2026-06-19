"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/app/context/AuthContext";
import { AuthGuard } from "./AuthGuard";
import { ErrorBoundary } from "./ErrorBoundary";

const navItems = [
    { href: "/dashboard",    label: "Dashboard" },
    { href: "/integrations", label: "Integrations" },
    { href: "/analysis",     label: "CSV Analysis" },
    { href: "/import",       label: "Import" },
    { href: "/settings",     label: "Settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    return (
        <AuthGuard>
            <div className="min-h-screen bg-gray-50">
                {/* Navigation */}
                <nav className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-40">
                    <div className="max-w-7xl mx-auto px-8 flex items-center justify-between h-14">
                        <div className="flex items-center gap-8">
                            <Link href="/dashboard" className="text-lg font-bold text-indigo-600">
                                SparqAI
                            </Link>
                            <div className="flex items-center gap-1">
                                {navItems.map((item) => (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition ${
                                            pathname === item.href || pathname.startsWith(item.href + "/")
                                                ? "text-indigo-700 bg-indigo-50"
                                                : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                                        }`}
                                    >
                                        {item.label}
                                    </Link>
                                ))}
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <Link
                                href="/settings/team"
                                className="text-xs text-gray-500 hover:text-gray-700 transition"
                            >
                                Team
                            </Link>
                            <Link
                                href="/settings/audit"
                                className="text-xs text-gray-500 hover:text-gray-700 transition"
                            >
                                Audit Log
                            </Link>
                            {user && (
                                <div className="flex items-center gap-3 ml-2 pl-4 border-l border-gray-200">
                                    <span className="text-xs text-gray-500">{user.email}</span>
                                    <button
                                        onClick={logout}
                                        className="text-xs text-red-500 hover:text-red-700 transition"
                                    >
                                        Logout
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </nav>

                {/* Page content */}
                <ErrorBoundary>
                    {children}
                </ErrorBoundary>
            </div>
        </AuthGuard>
    );
}
