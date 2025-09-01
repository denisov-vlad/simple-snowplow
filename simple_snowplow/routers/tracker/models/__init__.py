"""
Schema definitions for Snowplow events.
"""

from .sendgrid import SendgridElementBaseModel, SendgridModel
from .snowplow import (
    Model,
    PayloadElementBaseModel,
    PayloadElementPostModel,
    PayloadModel,
    SnowPlowModel,
    StructuredEvent,
)

__all__ = [
    "Model",
    "SnowPlowModel",
    "StructuredEvent",
    "PayloadElementBaseModel",
    "PayloadElementPostModel",
    "PayloadModel",
    "SendgridElementBaseModel",
    "SendgridModel",
]
