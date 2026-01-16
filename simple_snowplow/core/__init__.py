"""
Core module for Simple Snowplow.

This module provides core functionality including configuration,
dependency injection, exception handling, and protocols.
"""

from .config import Settings, get_settings, settings
from .constants import APP_NAME, APP_SLUG, APP_VERSION
from .dependencies import DbClient, DbConnector, Dependencies, get_db_connector
from .exceptions import (
    ConfigurationError,
    DatabaseError,
    ParsingError,
    ProxyError,
    SimpleSnowplowError,
    ValidationError,
)
from .protocols import DatabaseConnector, EventHandler, PayloadParser

__all__ = [
    # Configuration
    "Settings",
    "get_settings",
    "settings",
    # Constants
    "APP_NAME",
    "APP_SLUG",
    "APP_VERSION",
    # Dependencies
    "Dependencies",
    "DbConnector",
    "DbClient",
    "get_db_connector",
    # Exceptions
    "SimpleSnowplowError",
    "DatabaseError",
    "ConfigurationError",
    "ParsingError",
    "ProxyError",
    "ValidationError",
    # Protocols
    "DatabaseConnector",
    "PayloadParser",
    "EventHandler",
]
