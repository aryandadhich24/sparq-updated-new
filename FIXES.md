# Auth & Integration Fixes — SparqAI

## Root Causes Fixed

### 1. Login Broken — `Content-Type` mismatch (CRITICAL)
**File:** `frontend/lib/api.ts` → `loginWithCredentials()`

The original code used `new FormData()` which sends `multipart/form-data`.
FastAPI's `OAuth2PasswordRequestForm` **requires** `application/x-www-form-urlencoded`.

```diff
- const formData = new FormData();
- formData.append('username', email);
- formData.append('password', password);
- const res = await fetch(`${API_BASE}/auth/login`, { method: 'POST', body: formData });
+ const body = new URLSearchParams();
+ body.append('username', email);   // OAuth2 spec field name
+ body.append('password', password);
+ const res = await fetch(`${API_BASE}/auth/login`, { method: 'POST', body });
```

`URLSearchParams` automatically sets `Content-Type: application/x-www-form-urlencoded`.

---

### 2. No Loading States — Double Submit / Silent Failures
**Files:** `frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`

Added `loading` state + disabled buttons + spinner during API calls.

---

### 3. AuthContext — Race Condition on Concurrent fetchUser Calls
**File:** `frontend/app/context/AuthContext.tsx`

Added `fetchingRef` guard to prevent multiple simultaneous `/auth/me` calls
on mount (can happen in React Strict Mode).

---

### 4. OAuth Callback — `api.exchangeToken` not in original `api.ts`
**File:** `frontend/app/integrations/callback/page.tsx`

The callback page called `api.exchangeToken(...)` but the method existed
in a different form. Fixed the callback to properly handle:
- OAuth errors returned by provider (e.g. `?error=access_denied`)
- Missing `code` param
- Auth context still loading when callback fires
- Visual states: loading spinner → success tick → error cross

---

### 5. Register Page — No Password Confirmation or Strength Indicator
**File:** `frontend/app/register/page.tsx`

Added confirm password field with mismatch indicator, and a 5-step
password strength meter (checks length, uppercase, digits, symbols).

---

### 6. Forgot Password Flow
**File:** `frontend/app/login/page.tsx`

Added an inline "Forgot Password" view that calls `POST /auth/forgot-password`.
Always shows success to prevent email enumeration.

---

## Environment Setup

```bash
# backend/.env  (copy from .env.example and fill in)
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=postgresql://user:password@localhost:5432/roi_db
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
FRONTEND_URL=http://localhost:3000

# HubSpot OAuth (leave blank to use mock data)
HUBSPOT_CLIENT_ID=
HUBSPOT_CLIENT_SECRET=
HUBSPOT_REDIRECT_URI=http://localhost:8000/api/v1/integrations/hubspot/callback

# Salesforce OAuth (leave blank to use mock data)
SALESFORCE_CLIENT_ID=
SALESFORCE_CLIENT_SECRET=
SALESFORCE_REDIRECT_URI=http://localhost:8000/api/v1/integrations/salesforce/callback
```

Without client IDs set, **both HubSpot and Salesforce run in mock mode** — 
they return realistic demo data so the full connect → sync → dashboard flow
works without real credentials.

---

## HubSpot & Salesforce Integration Flow

```
1. User clicks "Connect HubSpot" on /integrations
2. Frontend → GET /api/v1/integrations/hubspot/authorize   (returns OAuth URL)
3. Browser → redirects to HubSpot OAuth consent screen
4. HubSpot → redirects to /api/v1/integrations/hubspot/callback?code=...
5. Backend → redirects to /integrations/callback?code=...&provider=hubspot&state=...
6. Frontend callback page → POST /api/v1/integrations/hubspot/exchange?code=...
7. Backend stores encrypted token → returns { message: "HubSpot connected" }
8. User clicks "Sync Now" → POST /api/v1/integrations/hubspot/ingest
9. Deals imported as Outcome records, attribution recalculated
```

Same flow for Salesforce (Opportunities → Outcomes).

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/lib/api.ts` | Fixed `loginWithCredentials` to use `URLSearchParams`; added full exchange/sync methods |
| `frontend/app/login/page.tsx` | Loading state, error display, forgot-password inline flow |
| `frontend/app/register/page.tsx` | Password confirm, strength meter, loading state |
| `frontend/app/context/AuthContext.tsx` | `fetchingRef` race guard, cleaner error handling |
| `frontend/app/integrations/callback/page.tsx` | Full error handling, loading/success/error UI states |
