"""
Base router classes for Simple Snowplow.

This module provides base classes for router implementations with
common functionality like route registration and middleware.
"""

from abc import ABC
from typing import Callable

from fastapi import APIRouter, Depends
from fastapi.security import APIKeyHeader


class BaseRouter(ABC):
    """
    Base router class with common functionality.

    Provides a structured way to create routers with consistent
    configuration and optional security.

    Attributes:
        router: The underlying FastAPI router
        security: Optional API key security dependency

    Example:
        >>> class MyRouter(BaseRouter):
        ...     def __init__(self):
        ...         super().__init__(prefix="/api", tags=["my-api"])
        ...         self._register_routes()
        ...
        ...     def _register_routes(self):
        ...         self.router.get("/")(self.get_items)
        ...
        ...     async def get_items(self):
        ...         return {"items": []}
    """

    def __init__(
        self,
        prefix: str = "",
        tags: list[str] | None = None,
        include_in_schema: bool = True,
        security: APIKeyHeader | None = None,
        dependencies: list | None = None,
    ):
        """
        Initialize the base router.

        Args:
            prefix: URL prefix for all routes
            tags: OpenAPI tags for documentation
            include_in_schema: Whether to include routes in OpenAPI schema
            security: Optional API key security dependency
            dependencies: List of dependencies to apply to all routes
        """
        self._prefix = prefix
        self._tags = tags or []
        self._security = security

        self.router = APIRouter(
            prefix=prefix,
            tags=tags,
            include_in_schema=include_in_schema,
            dependencies=dependencies or [],
        )

    @property
    def prefix(self) -> str:
        """Get the router prefix."""
        return self._prefix

    @property
    def tags(self) -> list[str]:
        """Get the router tags."""
        return self._tags

    def get_security_dependency(self):
        """
        Get security dependency for protected routes.

        Returns:
            Depends instance if security is configured, None otherwise
        """
        if self._security:
            return Depends(self._security)
        return None

    def include_router(self, router: APIRouter, **kwargs) -> None:
        """
        Include another router.

        Args:
            router: The router to include
            **kwargs: Additional arguments for include_router
        """
        self.router.include_router(router, **kwargs)

    def add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: list[str] | None = None,
        **kwargs,
    ) -> None:
        """
        Add a route to the router.

        Args:
            path: The URL path
            endpoint: The route handler function
            methods: HTTP methods (default: ["GET"])
            **kwargs: Additional arguments for add_api_route
        """
        methods = methods or ["GET"]
        self.router.add_api_route(path, endpoint, methods=methods, **kwargs)


class ProtectedRouter(BaseRouter):
    """
    Router that requires API key authentication for all routes.

    All routes registered on this router will require a valid API key.
    """

    def __init__(
        self,
        prefix: str = "",
        tags: list[str] | None = None,
        api_key_header: str = "X-API-Key",
        **kwargs,
    ):
        """
        Initialize a protected router.

        Args:
            prefix: URL prefix for all routes
            tags: OpenAPI tags for documentation
            api_key_header: Name of the API key header
            **kwargs: Additional arguments for BaseRouter
        """
        security = APIKeyHeader(name=api_key_header, auto_error=True)
        super().__init__(
            prefix=prefix,
            tags=tags,
            security=security,
            dependencies=[Depends(security)],
            **kwargs,
        )
