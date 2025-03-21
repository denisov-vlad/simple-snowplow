"""
Enum definitions used in ClickHouse schemas.
"""

from enum import Enum


class Platform(Enum):
    """
    Platform type enum.
    """

    web = 1
    mob = 2
    pc = 3
    srv = 4
    app = 5
    tv = 6
    cnsl = 7
    iot = 8


class EventType(Enum):
    """
    Event type enum.
    """

    pv = 1  # Page view
    pp = 2  # Page ping
    ue = 3  # Unstructured event
    se = 4  # Structured event
    tr = 5  # Transaction
    ti = 6  # Transaction item
    s = 7  # Session
