"""
Base middleware classes for Simple Snowplow.
"""
from typing import Callable

from fastapi import Request
from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class BaseMiddleware(BaseHTTPMiddleware):
    """Base middleware class with common functionality."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process the request and return the response."""
        return await call_next(request)

    async def process_request(self, request: Request) -> None:
        """Process the incoming request."""
        pass

    async def process_response(self, response: Response) -> None:
        """Process the outgoing response."""
        pass
