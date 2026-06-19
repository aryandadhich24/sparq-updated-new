import * as Sentry from '@sentry/nextjs';

Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    tracesSampleRate: 1.0,
    environment: process.env.NODE_ENV,
    // Enable this to capture replays on errors
    replaysOnErrorSampleRate: 1.0,
    replaysSessionSampleRate: 0.1,
});
