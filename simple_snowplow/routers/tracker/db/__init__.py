"""
Database integrations for the Simple Snowplow tracker.
"""

# Import all public components from specific database backends
from .clickhouse import (
    ClickHouseConnector,
    EventType,
    Platform,
    TableManager,
    get_fields_for_table_group,
    register_fields,
)

__all__ = [
    # Re-export components from ClickHouse module
    "ClickHouseConnector",
    "TableManager",
    "get_fields_for_table_group",
    "register_fields",
    "Platform",
    "EventType",
]
