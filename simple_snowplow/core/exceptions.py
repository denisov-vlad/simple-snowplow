"""
Custom exception classes for Simple Snowplow.

This module defines a hierarchy of exceptions used throughout the application
to provide consistent error handling and meaningful error messages.
"""

from typing import Any


class SimpleSnowplowError(Exception):
    """Base exception for all Simple Snowplow errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# Database Exceptions
class DatabaseError(SimpleSnowplowError):
    """Base exception for database-related errors."""

    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    pass


class QueryError(DatabaseError):
    """Raised when a database query fails."""

    pass


class InsertError(DatabaseError):
    """Raised when inserting data into the database fails."""

    pass


class TableNotFoundError(DatabaseError):
    """Raised when a required table doesn't exist."""

    pass


# Configuration Exceptions
class ConfigurationError(SimpleSnowplowError):
    """Base exception for configuration-related errors."""

    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration values are invalid."""

    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""

    pass


# Parsing Exceptions
class ParsingError(SimpleSnowplowError):
    """Base exception for data parsing errors."""

    pass


class PayloadParsingError(ParsingError):
    """Raised when payload parsing fails."""

    pass


class UserAgentParsingError(ParsingError):
    """Raised when user agent parsing fails."""

    pass


class IPParsingError(ParsingError):
    """Raised when IP address parsing fails."""

    pass


# Proxy Exceptions
class ProxyError(SimpleSnowplowError):
    """Base exception for proxy-related errors."""

    pass


class ProxyTimeoutError(ProxyError):
    """Raised when a proxy request times out."""

    pass


class ProxyRequestError(ProxyError):
    """Raised when a proxy request fails."""

    pass


# Rate Limiting Exceptions
class RateLimitExceededError(SimpleSnowplowError):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int, client_ip: str):
        self.retry_after = retry_after
        self.client_ip = client_ip
        super().__init__(
            f"Rate limit exceeded for {client_ip}",
            {"retry_after": retry_after, "client_ip": client_ip},
        )


# Validation Exceptions
class ValidationError(SimpleSnowplowError):
    """Base exception for validation errors."""

    pass


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""

    pass
