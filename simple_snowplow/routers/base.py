"""
Base router classes for Simple Snowplow.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.security import APIKeyHeader


class BaseRouter:
    """Base router class with common functionality."""

    def __init__(
        self,
        prefix: str,
        tags: list[str],
        include_in_schema: bool = True,
        security: Optional[APIKeyHeader] = None,
    ):
        self.router = APIRouter(
            prefix=prefix,
            tags=tags,
            include_in_schema=include_in_schema,
        )
        self.security = security

    def get_current_user(self):
        """Get current user from security dependency."""
        if self.security:
            return Depends(self.security)
        return None

    def include_router(self, router: APIRouter) -> None:
        """Include another router."""
        self.router.include_router(router)
