"""
Dependency injection for Simple Snowplow.
"""

from typing import Annotated

from fastapi import Depends, Request

from .protocols import RowSink


def get_db_connector(request: Request) -> RowSink:
    """Return the active ingest connector from application state."""
    return request.app.state.connector


DbConnector = Annotated[RowSink, Depends(get_db_connector)]
