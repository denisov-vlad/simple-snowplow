"""
Rate limiting middleware for Simple Snowplow.

Implements IP-based rate limiting with configurable limits, whitelists,
and sliding window tracking.
"""

import ipaddress
import random
import time
from typing import ClassVar

from core.config import settings
from core.constants import CLEANUP_PROBABILITY, HTTP_429_DESCRIPTION
from fastapi import Request, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from .base import BaseMiddleware

SECURITY_CONFIG = settings.security
RATE_LIMITING_CONFIG = SECURITY_CONFIG.rate_limiting


class RateLimitMiddleware(BaseMiddleware):
    """
    IP-based rate limiting middleware.

    Tracks request counts per IP address with a sliding window algorithm.
    Supports IP and path whitelisting for bypassing rate limits.
    """

    # Shared storage for IP request counts (IP -> (count, window_start))
    _ip_request_counts: ClassVar[dict[str, tuple[int, float]]] = {}

    async def should_process(self, request: Request) -> bool:
        """Only process if rate limiting is enabled."""
        return RATE_LIMITING_CONFIG.enabled

    async def process_request(self, request: Request) -> Response | None:
        """
        Check rate limit and return 429 if exceeded.

        Args:
            request: The incoming request

        Returns:
            429 Response if rate limited, None otherwise
        """
        client_ip = self._get_client_ip(request)

        # Skip rate limiting for whitelisted IPs or paths
        if self._is_whitelisted(client_ip, request.url.path):
            return None

        # Check and update rate limit
        response = self._check_rate_limit(client_ip)

        # Probabilistic cleanup of old entries
        if random.random() < CLEANUP_PROBABILITY:
            self._cleanup_old_entries()

        return response

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.

        Handles X-Forwarded-For header when behind a proxy.

        Args:
            request: The incoming request

        Returns:
            The client IP address
        """
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")

        if forwarded_for and SECURITY_CONFIG.trust_proxy_headers:
            # Get the first IP in the chain (original client)
            client_ip = forwarded_for.split(",")[0].strip()

        return client_ip

    def _is_whitelisted(self, ip: str, path: str) -> bool:
        """
        Check if the IP or path is whitelisted.

        Args:
            ip: Client IP address
            path: Request path

        Returns:
            True if whitelisted, False otherwise
        """
        # Check IP whitelist
        for whitelisted_ip in RATE_LIMITING_CONFIG.ip_whitelist:
            try:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(
                    whitelisted_ip,
                    strict=False,
                ):
                    return True
            except ValueError:
                # Invalid IP format, skip
                pass

        # Check path whitelist
        for whitelisted_path in RATE_LIMITING_CONFIG.path_whitelist:
            if path.startswith(whitelisted_path):
                return True

        return False

    def _check_rate_limit(self, client_ip: str) -> Response | None:
        """
        Check if the client has exceeded the rate limit.

        Args:
            client_ip: The client IP address

        Returns:
            429 Response if rate limited, None otherwise
        """
        now = time.time()
        window_seconds = RATE_LIMITING_CONFIG.window_seconds
        max_requests = RATE_LIMITING_CONFIG.max_requests

        if client_ip in self._ip_request_counts:
            count, window_start = self._ip_request_counts[client_ip]

            # Reset count if window has expired
            if now - window_start > window_seconds:
                self._ip_request_counts[client_ip] = (1, now)
            else:
                # Increment counter
                count += 1
                if count > max_requests:
                    # Rate limit exceeded
                    retry_after = int(window_start + window_seconds - now)
                    return Response(
                        content=HTTP_429_DESCRIPTION,
                        status_code=HTTP_429_TOO_MANY_REQUESTS,
                        headers={"Retry-After": str(max(1, retry_after))},
                    )
                self._ip_request_counts[client_ip] = (count, window_start)
        else:
            # First request from this IP
            self._ip_request_counts[client_ip] = (1, now)

        return None

    def _cleanup_old_entries(self) -> None:
        """Remove expired entries from the tracking dictionary."""
        now = time.time()
        expired_time = now - RATE_LIMITING_CONFIG.window_seconds

        expired_ips = [
            ip
            for ip, (_, window_start) in self._ip_request_counts.items()
            if window_start < expired_time
        ]

        for ip in expired_ips:
            del self._ip_request_counts[ip]
