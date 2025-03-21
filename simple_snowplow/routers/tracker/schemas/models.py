"""
Data models for Snowplow events.
"""

from datetime import datetime
from typing import Any, List

from fastapi import Query
from fastapi.exceptions import RequestValidationError
from json_repair import repair_json
from pydantic import AliasChoices, BaseModel, Field
from typing_extensions import Self


class Model(BaseModel):
    """Base model with enhanced JSON validation."""

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        context: Any = None,
    ) -> Self:
        """
        Validate the given JSON data against the Pydantic model with auto-repair.

        Args:
            json_data: The JSON data to validate
            strict: Whether to enforce types strictly
            context: Extra variables to pass to the validator

        Returns:
            The validated Pydantic model

        Raises:
            ValidationError: If the object could not be validated after repair
        """
        # Hide this function from tracebacks
        __tracebackhide__ = True
        kwargs = {"input": json_data, "strict": strict, "context": context}

        try:
            return cls.__pydantic_validator__.validate_json(**kwargs)
        except RequestValidationError:
            # Try to repair the JSON if standard parsing fails
            kwargs["input"] = repair_json(json_data)

        return cls.__pydantic_validator__.validate_json(**kwargs)


class SnowPlowModel(Model):
    """Base model for Snowplow data."""

    data: List[Any | None] = Query(...)
    json_schema: str | None = Query(
        None,
        alias="schema",
        title="Snowplow schema definition",
    )


class StructuredEvent(Model):
    """Model for structured events."""

    se_ac: str = Query(
        "",
        title="Event action",
        description="Only for event_type = se",
        validation_alias=AliasChoices("se_ac", "action"),
    )
    se_ca: str = Query(
        "",
        title="Event category",
        description="Only for event_type = se",
        validation_alias=AliasChoices("se_ca", "category"),
    )
    se_la: str = Query(
        "",
        title="Event label",
        description="Only for event_type = se",
        validation_alias=AliasChoices("se_la", "label"),
    )
    se_pr: str = Query(
        "",
        title="Event property",
        description="Only for event_type = se",
        validation_alias=AliasChoices("se_pr", "property"),
    )
    se_va: str = Query(
        "",
        title="Event value",
        description="Only for event_type = se",
        validation_alias=AliasChoices("se_va", "value"),
    )


class PayloadElementBaseModel(StructuredEvent):
    """Base model for payload elements (common to GET and POST)."""

    # URL and referrer fields
    url: str = Query("", title="Page URL")
    refr: str = Query("", title="Referrer URL")
    page: str = Query("", title="Page title")

    # Identifiers
    aid: str = Query(..., title="Unique identifier for website / application")
    eid: str | None = Query(None, title="Event UUID")
    duid: str | None = Query(
        None,
        title="Unique identifier for a user, based on a first party cookie",
    )
    uid: str = Query(
        "",
        title="Unique identifier for user, set by the business using setUserId",
    )
    sid: str | None = Query(
        None,
        title="Unique identifier (UUID) for this visit of this user_id to this domain",
    )
    vid: int | None = Query(
        None,
        title="Index of number of visits that this user_id has made to this domain",
    )

    # Event type and timestamps
    e: str = Query(
        ...,
        title="Event type",
        description="pv = page view, pp = page ping, ue = unstructured event, "
        "se = structured event, tr = transaction, ti = transaction item",
    )
    dtm: datetime = Field(
        default_factory=lambda: datetime.now(),
        title="Timestamp when event occurred, as recorded by client device",
    )
    stm: datetime | None = Field(
        default_factory=lambda: datetime.now(),
        title="Timestamp when event was sent by client device to collector",
    )

    # Platform and environment
    p: str = Query(..., title="The platform the app runs on", description="ex. web")
    tv: str = Query(..., title="Identifier for Snowplow tracker")
    tna: str = Query("", title="The tracker namespace")
    tz: str | None = Query(None, title="Time zone of client device's OS")
    lang: str = Query("", title="Language the browser is set to")

    # Browser/viewport information
    cs: str = Query("", title="Web page's character encoding", description="ex. UTF-8")
    res: str = Query(..., title="Screen / monitor resolution")
    vp: str = Query("0x0", title="Browser viewport width and height")
    ds: str = Query("0x0", title="Web page width and height")
    cd: int = Query(0, title="Browser color depth")
    cookie: int | None = Query(None, title="Does the browser permit cookies?")

    # Page ping information (for pp event type)
    pp_mix: int = Query(0, title="Minimum page x offset seen in the last ping period")
    pp_max: int = Query(0, title="Maximum page x offset seen in the last ping period")
    pp_miy: int = Query(0, title="Minimum page y offset seen in the last ping period")
    pp_may: int = Query(0, title="Maximum page y offset seen in the last ping period")

    # Context information
    co: str | None = Query(None, title="An array of custom contexts")
    cx: str | None = Query(None, title="An array of custom contexts (b64)")

    # Unstructured event information
    ue_pr: str = Query("", title="The properties of the event")
    ue_px: str = Query("", title="The properties of the event (b64)")


class PayloadElementPostModel(PayloadElementBaseModel):
    """Model for POST payload elements with received timestamp."""

    rtm: datetime = Field(
        default_factory=lambda: datetime.now(),
        title="Timestamp when event was received by collector",
    )


class PayloadModel(SnowPlowModel):
    """Model for batch payloads."""

    data: List[PayloadElementPostModel] = Query([])


class SendgridElementBaseModel(Model):
    """Model for Sendgrid webhook events."""

    email: str = Query(..., title="Email address")
    timestamp: datetime = Query(..., title="Event timestamp")
    smtp_id: str = Query(..., validation_alias="smtp-id", title="SMTP ID")
    event: str = Query(..., title="Event type")
    category: List[str] = Query(..., title="Event categories")
    sg_event_id: str = Query(..., title="SendGrid event ID")
    sg_message_id: str = Query(..., title="SendGrid message ID")
    response: str = Query("", title="Response")
    attempt: int = Query(0, title="Attempt number")
    useragent: str = Query("", title="User agent string")
    ip: str = Query("", title="IP address")
    url: str = Query("", title="URL")
    reason: str = Query("", title="Reason")
    status: str = Query("", title="Status")
    asm_group_id: int = Query(0, title="ASM Group ID")


class SendgridModel(Model):
    """Model for batch Sendgrid events."""

    data: List[SendgridElementBaseModel] = Query([])
