"""
Dependency injection for Simple Snowplow.

This module provides FastAPI dependencies for accessing shared resources
like database connections, configuration, and other services.
"""

from typing import Annotated

from fastapi import Depends, Request

from .config import Settings, get_settings
from .protocols import DatabaseConnector


def get_db_connector(request: Request) -> DatabaseConnector:
    """
    Get the database connector from the application state.

    Args:
        request: The FastAPI request object

    Returns:
        The database connector instance
    """
    return request.app.state.connector


def get_db_client(request: Request):
    """
    Get the raw database client from the application state.

    Args:
        request: The FastAPI request object

    Returns:
        The raw database client
    """
    return request.app.state.ch_client


# Type aliases for dependency injection
DbConnector = Annotated[DatabaseConnector, Depends(get_db_connector)]
DbClient = Annotated[object, Depends(get_db_client)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class Dependencies:
    """
    Container for application dependencies.

    This class provides a centralized way to access and manage
    application-wide dependencies.
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    @property
    def settings(self) -> Settings:
        """Get application settings."""
        return self._settings

    def get_endpoint_config(self):
        """Get endpoint configuration."""
        return self._settings.common.snowplow.endpoints

    def get_security_config(self):
        """Get security configuration."""
        return self._settings.security

    def get_database_config(self):
        """Get database configuration."""
        return self._settings.clickhouse
