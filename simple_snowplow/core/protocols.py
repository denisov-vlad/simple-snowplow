"""
Protocol definitions for Simple Snowplow.

This module defines Protocol classes that specify the expected interfaces
for various components, enabling better type safety and duck typing support.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DatabaseConnector(Protocol):
    """Protocol for database connectors."""

    async def command(self, query: str) -> None:
        """Execute a database command."""
        ...

    async def query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a database query and return results."""
        ...

    async def insert_rows(
        self,
        rows: list[dict[str, Any]],
        table_group: str = "snowplow",
    ) -> None:
        """Insert rows into the database."""
        ...

    async def get_table_name(self, table_group: str = "snowplow") -> str:
        """Get the table name for a specific group."""
        ...


@runtime_checkable
class PayloadParser(Protocol):
    """Protocol for payload parsers."""

    async def parse(self, data: Any) -> dict[str, Any]:
        """Parse the input data and return a dictionary."""
        ...


@runtime_checkable
class EventHandler(Protocol):
    """Protocol for event handlers."""

    async def handle(self, event: dict[str, Any]) -> None:
        """Handle an event."""
        ...


@runtime_checkable
class HealthChecker(Protocol):
    """Protocol for health check implementations."""

    async def check(self) -> dict[str, bool]:
        """Perform health check and return status."""
        ...


@runtime_checkable
class TableManager(Protocol):
    """Protocol for database table managers."""

    async def create_database(self) -> None:
        """Create the database if it doesn't exist."""
        ...

    async def create_table(self, table_group: str) -> None:
        """Create a table for the specified group."""
        ...

    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        ...
