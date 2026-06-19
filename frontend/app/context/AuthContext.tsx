"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import { API_BASE } from "@/lib/api";

interface User {
    id: number;
    email: string;
    full_name?: string;
    organization_id?: number;
    role?: string;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string) => void;
    logout: () => void;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Refresh 1 hour before a 24-hour token expires
const REFRESH_INTERVAL_MS = 23 * 60 * 60 * 1000;

export const AUTH_LOGOUT_EVENT = "sparqai:force-logout";

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();
    const refreshTimer = useRef<NodeJS.Timeout | null>(null);
    // Prevent multiple simultaneous fetchUser calls
    const fetchingRef = useRef(false);

    const logout = useCallback(() => {
        if (refreshTimer.current) clearInterval(refreshTimer.current);
        localStorage.removeItem("access_token");
        setToken(null);
        setUser(null);
        if (pathname !== "/login" && pathname !== "/register") {
            router.push("/login");
        }
    }, [router, pathname]);

    useEffect(() => {
        const handler = () => logout();
        window.addEventListener(AUTH_LOGOUT_EVENT, handler);
        return () => window.removeEventListener(AUTH_LOGOUT_EVENT, handler);
    }, [logout]);

    const fetchUser = useCallback(async (authToken: string) => {
        if (fetchingRef.current) return;
        fetchingRef.current = true;
        try {
            const res = await fetch(`${API_BASE}/auth/me`, {
                headers: { Authorization: `Bearer ${authToken}` },
            });
            if (res.ok) {
                const userData = await res.json();
                setUser(userData);
            } else {
                // Token is invalid — clear it but don't redirect if already on public page
                localStorage.removeItem("access_token");
                setToken(null);
                setUser(null);
                if (pathname !== "/login" && pathname !== "/register") {
                    router.push("/login");
                }
            }
        } catch (error) {
            console.error("Failed to fetch user:", error);
            // Network error — keep token, user stays on page, will retry on next load
        } finally {
            setIsLoading(false);
            fetchingRef.current = false;
        }
    }, [router, pathname]);

    const scheduleRefresh = useCallback((currentToken: string) => {
        if (refreshTimer.current) clearInterval(refreshTimer.current);
        refreshTimer.current = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/auth/refresh`, {
                    method: "POST",
                    headers: { Authorization: `Bearer ${currentToken}` },
                });
                if (res.ok) {
                    const data = await res.json();
                    localStorage.setItem("access_token", data.access_token);
                    setToken(data.access_token);
                    currentToken = data.access_token;
                } else {
                    logout();
                }
            } catch {
                // Silently fail — retry on next interval
            }
        }, REFRESH_INTERVAL_MS);
    }, [logout]);

    // Bootstrap: read stored token on mount
    useEffect(() => {
        const storedToken = localStorage.getItem("access_token");
        if (storedToken) {
            setToken(storedToken);
            fetchUser(storedToken);
            scheduleRefresh(storedToken);
        } else {
            setIsLoading(false);
        }
        return () => {
            if (refreshTimer.current) clearInterval(refreshTimer.current);
        };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const login = useCallback((newToken: string) => {
        localStorage.setItem("access_token", newToken);
        setToken(newToken);
        fetchUser(newToken);
        scheduleRefresh(newToken);
        router.push("/dashboard");
    }, [fetchUser, scheduleRefresh, router]);

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
