"""
Constants and magic values for Simple Snowplow.

This module centralizes all constant values used throughout the application
to improve maintainability and reduce magic strings/numbers.
"""

import base64
from typing import Final

# Application metadata
APP_NAME: Final[str] = "Simple Snowplow"
APP_SLUG: Final[str] = "simple-snowplow"
APP_VERSION: Final[str] = "0.5.0"

# HTTP Status descriptions
HTTP_429_DESCRIPTION: Final[str] = "Too many requests"

# Tracking pixel (1x1 transparent GIF)
TRACKING_PIXEL: Final[bytes] = base64.b64decode(
    b"R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
)

# Content types
CONTENT_TYPE_GIF: Final[str] = "image/gif"
CONTENT_TYPE_JSON: Final[str] = "application/json"
CONTENT_TYPE_OCTET_STREAM: Final[str] = "application/octet-stream"

# Timeouts (in seconds)
DEFAULT_PROXY_TIMEOUT: Final[float] = 10.0
DEFAULT_DB_CONNECT_TIMEOUT: Final[int] = 10

# Rate limiting
DEFAULT_MAX_REQUESTS: Final[int] = 100
DEFAULT_WINDOW_SECONDS: Final[int] = 60
CLEANUP_PROBABILITY: Final[float] = 0.01

# Database defaults
DEFAULT_DATABASE_NAME: Final[str] = "snowplow"
DEFAULT_TABLE_GROUP: Final[str] = "snowplow"

# Security headers
SECURITY_HEADERS: Final[dict[str, str]] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
HSTS_HEADER: Final[str] = "max-age=31536000; includeSubDomains"

# Endpoint paths
DEFAULT_POST_ENDPOINT: Final[str] = "/tracker"
DEFAULT_GET_ENDPOINT: Final[str] = "/i"
DEFAULT_PROXY_ENDPOINT: Final[str] = "/proxy"
DEFAULT_SENDGRID_ENDPOINT: Final[str] = "/sendgrid"
DEFAULT_METRICS_PATH: Final[str] = "/metrics/"

# ClickHouse defaults
DEFAULT_CLICKHOUSE_HOST: Final[str] = "clickhouse"
DEFAULT_CLICKHOUSE_PORT: Final[int] = 8123
DEFAULT_CLICKHOUSE_INTERFACE: Final[str] = "http"
DEFAULT_CLICKHOUSE_USERNAME: Final[str] = "default"
DEFAULT_CLICKHOUSE_DATABASE: Final[str] = "default"

# Async insert settings for ClickHouse
CLICKHOUSE_ASYNC_SETTINGS: Final[dict[str, int]] = {
    "async_insert": 1,
    "wait_for_async_insert": 0,
}

# Log levels
LOG_LEVEL_DEBUG: Final[str] = "DEBUG"
LOG_LEVEL_INFO: Final[str] = "INFO"
LOG_LEVEL_WARNING: Final[str] = "WARNING"
LOG_LEVEL_ERROR: Final[str] = "ERROR"

# Environment names
ENV_PRODUCTION: Final[str] = "production"
ENV_DEVELOPMENT: Final[str] = "development"
SENTRY_ENV_PROD: Final[str] = "prod"
SENTRY_ENV_DEV: Final[str] = "dev"
