import '@testing-library/jest-dom'
import { vi, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Cleanup after each test to avoid leaking DOM state
afterEach(() => {
    cleanup()
})

// Mock window.URL.createObjectURL for CSV downloads
if (typeof window !== 'undefined') {
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    window.URL.revokeObjectURL = vi.fn()
}

// Mock next/navigation used by most components
vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: vi.fn(),
        replace: vi.fn(),
        back: vi.fn(),
        prefetch: vi.fn(),
    }),
    usePathname: () => '/dashboard',
    useSearchParams: () => new URLSearchParams(),
}))

// Mock next/link to render a plain anchor so tests can assert on href
vi.mock('next/link', () => ({
    __esModule: true,
    default: ({ children, href, ...rest }: { children: React.ReactNode; href: string; [key: string]: any }) => (
        <a href={href} {...rest}>{children}</a>
    ),
}))

// localStorage mock (jsdom provides one, but reset it between tests)
const localStorageMock = (() => {
    let store: Record<string, string> = {}
    return {
        getItem: vi.fn((key: string) => store[key] ?? null),
        setItem: vi.fn((key: string, value: string) => { store[key] = value }),
        removeItem: vi.fn((key: string) => { delete store[key] }),
        clear: vi.fn(() => { store = {} }),
        get length() { return Object.keys(store).length },
        key: vi.fn((i: number) => Object.keys(store)[i] ?? null),
    }
})()

Object.defineProperty(window, 'localStorage', { value: localStorageMock })
