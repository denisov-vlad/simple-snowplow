"""
Core module for Simple Snowplow.
"""

from .config import Settings, settings
from .constants import APP_NAME, APP_SLUG, APP_VERSION
from .dependencies import DbConnector, get_db_connector
from .exceptions import (
    DatabaseConnectionError,
    DatabaseError,
    SimpleSnowplowError,
)
from .protocols import DatabaseConnector, RowSink

__all__ = [
    "Settings",
    "settings",
    "APP_NAME",
    "APP_SLUG",
    "APP_VERSION",
    "DbConnector",
    "get_db_connector",
    "SimpleSnowplowError",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseConnector",
    "RowSink",
]
