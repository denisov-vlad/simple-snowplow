"""
Routers module for Simple Snowplow.

This module provides all API routers for the application, including
the main tracker, proxy, and demo routers.
"""

from .base import BaseRouter, ProtectedRouter

__all__ = [
    "BaseRouter",
    "ProtectedRouter",
]
