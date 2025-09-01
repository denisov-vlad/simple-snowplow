"""
Data models for Sendgrid events.
"""

from datetime import datetime

from pydantic import Field

from .base import Model


class SendgridElementBaseModel(Model):
    """Model for Sendgrid webhook events."""

    email: str = Field(..., title="Email address")
    timestamp: datetime = Field(..., title="Event timestamp")
    smtp_id: str = Field(..., validation_alias="smtp-id", title="SMTP ID")
    event: str = Field(..., title="Event type")
    category: list[str] = Field(..., title="Event categories")
    sg_event_id: str = Field(..., title="SendGrid event ID")
    sg_message_id: str = Field(..., title="SendGrid message ID")
    response: str = Field("", title="Response")
    attempt: int = Field(0, title="Attempt number")
    useragent: str = Field("", title="User agent string")
    ip: str = Field("", title="IP address")
    url: str = Field("", title="URL")
    reason: str = Field("", title="Reason")
    status: str = Field("", title="Status")
    asm_group_id: int = Field(0, title="ASM Group ID")


class SendgridModel(Model):
    """Model for batch Sendgrid events."""

    data: list[SendgridElementBaseModel] = Field([])
