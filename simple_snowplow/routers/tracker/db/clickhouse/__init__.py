"""
ClickHouse database integration for Simple Snowplow.
"""

from .connector import ClickHouseConnector
from .schemas import get_fields_for_table_group, register_fields
from .schemas.enums import EventType, Platform
from .table_manager import TableManager

__all__ = [
    "ClickHouseConnector",
    "TableManager",
    "get_fields_for_table_group",
    "register_fields",
    "Platform",
    "EventType",
]
