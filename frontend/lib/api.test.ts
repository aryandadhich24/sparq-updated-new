import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api, API_BASE } from './api'

// ---------------------------------------------------------------------------
// We test against the real `api` object, but mock global `fetch`.
// The setup file already assigns `global.fetch = vi.fn()`, so we cast it here.
// ---------------------------------------------------------------------------

const mockFetch = global.fetch as ReturnType<typeof vi.fn>

beforeEach(() => {
    vi.clearAllMocks()
    // Reset localStorage before each test
    localStorage.clear()
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Return a minimal Response-like object that `handleResponse` will accept. */
function okJson(body: unknown): Response {
    return {
        ok: true,
        status: 200,
        json: () => Promise.resolve(body),
    } as unknown as Response
}

function errorJson(status: number, detail: string): Response {
    return {
        ok: false,
        status,
        statusText: 'Error',
        json: () => Promise.resolve({ detail }),
    } as unknown as Response
}

function errorNoBody(status: number): Response {
    return {
        ok: false,
        status,
        statusText: 'Internal Server Error',
        json: () => Promise.reject(new Error('no body')),
    } as unknown as Response
}

// ---------------------------------------------------------------------------
// URL construction
// ---------------------------------------------------------------------------

describe('API_BASE', () => {
    it('defaults to http://localhost:8000/api/v1', () => {
        expect(API_BASE).toBe('http://localhost:8000/api/v1')
    })
})

describe('api URL construction', () => {
    it('fetchDecisions calls /decisions', async () => {
        mockFetch.mockResolvedValueOnce(okJson([]))

        await api.fetchDecisions()

        expect(mockFetch).toHaveBeenCalledTimes(1)
        const [url] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/decisions`)
    })

    it('fetchDecisionDetail calls /decisions/:id', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ id: 42 }))

        await api.fetchDecisionDetail(42)

        const [url] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/decisions/42`)
    })

    it('fetchDecisionInsight calls /decisions/:id/insight', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ text: 'insight' }))

        await api.fetchDecisionInsight(7)

        const [url] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/decisions/7/insight`)
    })

    it('seedData calls POST /seed', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ message: 'ok' }))

        await api.seedData()

        const [url, opts] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/seed`)
        expect(opts.method).toBe('POST')
    })

    it('resetData calls DELETE /reset', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ message: 'ok' }))

        await api.resetData()

        const [url, opts] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/reset`)
        expect(opts.method).toBe('DELETE')
    })

    it('bulkImportDecisions calls POST /import/decisions/bulk', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ message: 'ok', errors: [] }))

        await api.bulkImportDecisions([{ description: 'test' }])

        const [url, opts] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/import/decisions/bulk`)
        expect(opts.method).toBe('POST')
    })

    it('bulkImportOutcomes calls POST /import/outcomes/bulk', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ message: 'ok', errors: [] }))

        await api.bulkImportOutcomes([{ value: 100 }])

        const [url, opts] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/import/outcomes/bulk`)
        expect(opts.method).toBe('POST')
    })

    it('fetchAuditLogs includes page and per_page params', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ items: [] }))

        await api.fetchAuditLogs(2, 25)

        const [url] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/audit/?page=2&per_page=25`)
    })

    it('fetchAuditLogs defaults to page 1 and 50 per page', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ items: [] }))

        await api.fetchAuditLogs()

        const [url] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/audit/?page=1&per_page=50`)
    })

    it('ingestHubSpot calls POST /integrations/hubspot/ingest', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ created: 1, skipped: 0, message: 'ok' }))

        await api.ingestHubSpot()

        const [url, opts] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/integrations/hubspot/ingest`)
        expect(opts.method).toBe('POST')
    })

    it('ingestSalesforce calls POST /integrations/salesforce/ingest', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ created: 0, skipped: 0, message: 'ok' }))

        await api.ingestSalesforce()

        const [url, opts] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/integrations/salesforce/ingest`)
        expect(opts.method).toBe('POST')
    })

    it('getAuthUrl normalizes provider slug', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ url: 'https://example.com' }))

        await api.getAuthUrl('google_ads')

        const [url] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/integrations/google-ads/authorize`)
    })

    it('disconnectIntegration calls DELETE with normalized slug', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ message: 'ok' }))

        await api.disconnectIntegration('hubspot')

        const [url, opts] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/integrations/hubspot/disconnect`)
        expect(opts.method).toBe('DELETE')
    })

    it('syncAdPlatform calls POST /ads/:slug/sync', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ message: 'ok', created: 5, updated: 2 }))

        await api.syncAdPlatform('meta_ads')

        const [url, opts] = mockFetch.mock.calls[0]
        expect(url).toBe(`${API_BASE}/ads/meta-ads/sync`)
        expect(opts.method).toBe('POST')
    })
})

// ---------------------------------------------------------------------------
// Auth headers
// ---------------------------------------------------------------------------

describe('auth headers', () => {
    it('includes Authorization header when token is in localStorage', async () => {
        localStorage.setItem('access_token', 'test-jwt-token')
        mockFetch.mockResolvedValueOnce(okJson([]))

        await api.fetchDecisions()

        const [, opts] = mockFetch.mock.calls[0]
        expect(opts.headers).toEqual(
            expect.objectContaining({
                'Content-Type': 'application/json',
                Authorization: 'Bearer test-jwt-token',
            }),
        )
    })

    it('omits Authorization header when no token is stored', async () => {
        mockFetch.mockResolvedValueOnce(okJson([]))

        await api.fetchDecisions()

        const [, opts] = mockFetch.mock.calls[0]
        expect(opts.headers).toEqual({ 'Content-Type': 'application/json' })
        expect(opts.headers.Authorization).toBeUndefined()
    })

    it('register does not use getAuthHeaders (no Bearer token)', async () => {
        localStorage.setItem('access_token', 'should-not-appear')
        mockFetch.mockResolvedValueOnce(okJson({ id: 1 }))

        await api.register({
            email: 'test@example.com',
            password: 'pass123',
            full_name: 'Test User',
            organization_name: 'TestOrg',
        })

        const [, opts] = mockFetch.mock.calls[0]
        expect(opts.headers).toEqual({ 'Content-Type': 'application/json' })
    })

    it('loginWithCredentials sends FormData (no Content-Type json header)', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ access_token: 'tok', token_type: 'bearer' }))

        await api.loginWithCredentials('user@test.com', 'secret')

        const [, opts] = mockFetch.mock.calls[0]
        expect(opts.method).toBe('POST')
        expect(opts.body).toBeInstanceOf(FormData)
    })

    it('exchangeHubSpotCode uses the provided token, not localStorage', async () => {
        localStorage.setItem('access_token', 'stored-token')
        mockFetch.mockResolvedValueOnce(okJson({ message: 'ok' }))

        await api.exchangeHubSpotCode('auth-code-123', 'explicit-token')

        const [, opts] = mockFetch.mock.calls[0]
        expect(opts.headers.Authorization).toBe('Bearer explicit-token')
    })
})

// ---------------------------------------------------------------------------
// Request body
// ---------------------------------------------------------------------------

describe('request body serialization', () => {
    it('bulkImportDecisions sends JSON array in body', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ message: 'ok', errors: [] }))

        const payload = [{ description: 'Row 1', cost: 100 }]
        await api.bulkImportDecisions(payload)

        const [, opts] = mockFetch.mock.calls[0]
        expect(opts.body).toBe(JSON.stringify(payload))
    })

    it('updateOrgSettings wraps settings in { settings } envelope', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ id: 1, name: 'Org', settings: {} }))

        await api.updateOrgSettings({ theme: 'dark' })

        const [, opts] = mockFetch.mock.calls[0]
        expect(JSON.parse(opts.body)).toEqual({ settings: { theme: 'dark' } })
    })

    it('inviteMember sends email and role in body', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ message: 'ok', link: '', token: '' }))

        await api.inviteMember('new@test.com', 'viewer')

        const [, opts] = mockFetch.mock.calls[0]
        expect(JSON.parse(opts.body)).toEqual({ email: 'new@test.com', role: 'viewer' })
    })

    it('createCheckoutSession sends plan and billing_cycle', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ checkout_url: 'https://stripe.com' }))

        await api.createCheckoutSession('pro', 'annual')

        const [, opts] = mockFetch.mock.calls[0]
        expect(JSON.parse(opts.body)).toEqual({ plan: 'pro', billing_cycle: 'annual' })
    })
})

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

describe('error handling', () => {
    it('throws an error with detail from response body', async () => {
        mockFetch.mockResolvedValueOnce(errorJson(403, 'Forbidden: insufficient role'))

        await expect(api.fetchDecisions()).rejects.toThrow('Forbidden: insufficient role')
    })

    it('falls back to status text when body has no detail', async () => {
        mockFetch.mockResolvedValueOnce(errorNoBody(500))

        await expect(api.fetchDecisions()).rejects.toThrow('Internal Server Error')
    })

    it('includes status code in fallback message for non-parseable errors', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: false,
            status: 422,
            statusText: 'Unprocessable Entity',
            json: () => Promise.resolve({}),
        } as unknown as Response)

        await expect(api.fetchDecisions()).rejects.toThrow('Request failed (422)')
    })

    it('rejects on network failure', async () => {
        mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'))

        await expect(api.fetchDecisions()).rejects.toThrow('Failed to fetch')
    })
})

// ---------------------------------------------------------------------------
// Return values
// ---------------------------------------------------------------------------

describe('return values', () => {
    it('fetchDecisions returns the parsed JSON array', async () => {
        const data = [{ id: 1, description: 'Test' }]
        mockFetch.mockResolvedValueOnce(okJson(data))

        const result = await api.fetchDecisions()

        expect(result).toEqual(data)
    })

    it('fetchDecisionDetail returns the parsed decision object', async () => {
        const detail = { id: 5, description: 'Detail', related_outcomes: [] }
        mockFetch.mockResolvedValueOnce(okJson(detail))

        const result = await api.fetchDecisionDetail(5)

        expect(result).toEqual(detail)
    })

    it('loginWithCredentials returns token data', async () => {
        mockFetch.mockResolvedValueOnce(okJson({ access_token: 'jwt123', token_type: 'bearer' }))

        const result = await api.loginWithCredentials('a@b.com', 'pw')

        expect(result).toEqual({ access_token: 'jwt123', token_type: 'bearer' })
    })
})
