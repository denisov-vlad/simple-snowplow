"""
Security headers middleware for Simple Snowplow.

Adds security-related HTTP headers to all responses.
"""

from core.config import settings
from core.constants import HSTS_HEADER, SECURITY_HEADERS
from fastapi import Request, Response

from .base import BaseMiddleware

SECURITY_CONFIG = settings.security


class SecurityHeadersMiddleware(BaseMiddleware):
    """
    Middleware that adds security headers to all responses.

    Headers include:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Restrict browser features
    - Strict-Transport-Security: Enforce HTTPS (when enabled)
    """

    def __init__(self, app):
        super().__init__(app)
        # Build headers dict once at initialization
        self._headers = self._build_headers()

    def _build_headers(self) -> dict[str, str]:
        """Build the security headers dictionary."""
        headers = dict(SECURITY_HEADERS)

        # Add HSTS header if HTTPS redirect is enabled
        if SECURITY_CONFIG.enable_https_redirect:
            headers["Strict-Transport-Security"] = HSTS_HEADER

        return headers

    async def process_response(
        self,
        request: Request,
        response: Response,
    ) -> Response:
        """Add security headers to the response."""
        for header_name, header_value in self._headers.items():
            if header_value:  # Only set non-empty headers
                response.headers[header_name] = header_value

        return response
