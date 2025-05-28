"""
Schema definitions for ClickHouse tables in Simple Snowplow.
"""

from .snowplow import ColumnDef, TupleColumnDef, snowplow_fields

# Map of table groups to their field definitions
_FIELD_REGISTRY = {
    "snowplow": snowplow_fields,
}


def register_fields(table_group: str, fields: list[ColumnDef | TupleColumnDef]) -> None:
    """
    Register fields for a table group.

    Args:
        table_group: The table group name
        fields: List of field definitions
    """
    _FIELD_REGISTRY[table_group] = fields


def get_fields_for_table_group(table_group: str) -> list[ColumnDef | TupleColumnDef]:
    """
    Get field definitions for a table group.

    Args:
        table_group: The table group name

    Returns:
        List of field definitions

    Raises:
        KeyError: If the table group is not registered
    """
    return _FIELD_REGISTRY[table_group]
