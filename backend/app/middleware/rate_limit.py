"""
Sliding-window rate limiter per IP address.

Notes for production:
- This is in-memory and per-process. Behind ECS with multiple tasks,
  each task enforces its own limit independently.
- For strict global enforcement, swap to Redis (INCR + EXPIRE) or
  rely on ALB/WAF request-rate rules.
- Periodic cleanup prevents memory growth from transient IPs.
"""

import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Clean up stale IPs every 5 minutes
_CLEANUP_INTERVAL = 300


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter per client IP."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _get_client_ip(self, request: Request) -> str:
        """Resolve client IP, respecting X-Forwarded-For behind ALB."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup_stale(self, now: float):
        """Remove entries for IPs with no recent requests."""
        if now - self._last_cleanup < _CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        stale = [ip for ip, ts in self.requests.items() if not ts or now - ts[-1] > 120]
        for ip in stale:
            del self.requests[ip]

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()
        window = 60.0  # 1 minute

        # Periodic cleanup
        self._cleanup_stale(now)

        # Clean old entries for this IP
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if now - t < window
        ]

        if len(self.requests[client_ip]) >= self.rpm:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        self.requests[client_ip].append(now)
        response = await call_next(request)
        return response
