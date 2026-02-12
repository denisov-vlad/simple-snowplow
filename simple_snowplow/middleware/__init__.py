"""
Middleware module for Simple Snowplow.

This module provides middleware components for request/response processing
including security headers.
"""

from .base import BaseMiddleware
from .security import SecurityHeadersMiddleware

__all__ = [
    "BaseMiddleware",
    "SecurityHeadersMiddleware",
]
