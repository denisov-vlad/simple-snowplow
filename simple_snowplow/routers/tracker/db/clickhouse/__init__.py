"""
ClickHouse database integration for Simple Snowplow.
"""
from .connector import ClickHouseConnector
from .schemas import get_fields_for_table_group
from .schemas import register_fields
from .schemas.enums import EventType
from .schemas.enums import Platform
from .table_manager import TableManager

__all__ = [
    "ClickHouseConnector",
    "TableManager",
    "get_fields_for_table_group",
    "register_fields",
    "Platform",
    "EventType",
]
