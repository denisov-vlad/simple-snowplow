import ipaddress
import random
import time

from core.config import settings
from fastapi import Request
from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


SECURITY_CONFIG = settings.security
RATE_LIMITING_CONFIG = SECURITY_CONFIG.rate_limiting

# IP-based rate limiting storage
ip_request_counts = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not RATE_LIMITING_CONFIG.enabled:
            return await call_next(request)

        # Get client IP, handle X-Forwarded-For if behind proxy
        client_ip = request.client.host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for and SECURITY_CONFIG.trust_proxy_headers:
            # Get the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()

        # Skip rate limiting for whitelisted IPs or paths
        if self._is_whitelisted(client_ip, request.url.path):
            return await call_next(request)

        # Check if IP has exceeded rate limit
        now = time.time()
        if client_ip in ip_request_counts:
            requests, window_start = ip_request_counts[client_ip]

            # Reset count if window has expired
            if now - window_start > RATE_LIMITING_CONFIG.window_seconds:
                ip_request_counts[client_ip] = (1, now)
            else:
                # Increment counter
                requests += 1
                if requests > RATE_LIMITING_CONFIG.max_requests:
                    # Rate limit exceeded
                    return Response(
                        content="Too many requests",
                        status_code=HTTP_429_TOO_MANY_REQUESTS,
                        headers={
                            "Retry-After": str(
                                int(
                                    window_start
                                    + RATE_LIMITING_CONFIG.window_seconds
                                    - now,
                                ),
                            ),
                        },
                    )
                ip_request_counts[client_ip] = (requests, window_start)
        else:
            # First request from this IP
            ip_request_counts[client_ip] = (1, now)

        # Clean up old entries occasionally (1% chance)
        if random.random() < 0.01:
            self._cleanup_old_entries(now)

        return await call_next(request)

    def _is_whitelisted(self, ip, path):
        # Check IP whitelist
        for whitelisted_ip in RATE_LIMITING_CONFIG.ip_whitelist:
            try:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(whitelisted_ip):
                    return True
            except ValueError:
                pass

        # Check path whitelist
        for whitelisted_path in RATE_LIMITING_CONFIG.path_whitelist:
            if path.startswith(whitelisted_path):
                return True

        return False

    def _cleanup_old_entries(self, now):
        expired_time = now - RATE_LIMITING_CONFIG.window_seconds
        for ip in list(ip_request_counts.keys()):
            if ip_request_counts[ip][1] < expired_time:
                del ip_request_counts[ip]
