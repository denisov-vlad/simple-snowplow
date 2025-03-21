from core.config import settings
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

SECURITY_CONFIG = settings.security
ENABLE_HTTPS_REDIRECT = SECURITY_CONFIG.enable_https_redirect
TRUSTED_HOSTS = SECURITY_CONFIG.trusted_hosts

# Security settings
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": (
        "max-age=31536000; includeSubDomains"
        if SECURITY_CONFIG.enable_https_redirect
        else ""
    ),
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers to all responses
        for header_name, header_value in SECURITY_HEADERS.items():
            if header_value:  # Only set non-empty headers
                response.headers[header_name] = header_value

        return response
