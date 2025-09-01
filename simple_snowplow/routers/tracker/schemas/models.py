"""
Data models for Snowplow events.
"""

from datetime import datetime
from typing import Any, Literal, Self

from fastapi.exceptions import RequestValidationError
from json_repair import repair_json
from pydantic import AliasChoices, BaseModel, Field

from uuid import UUID


class Model(BaseModel):
    """Base model with enhanced JSON validation."""

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray | memoryview,  # added memoryview
        *,
        strict: bool | None = None,
        context: Any = None,
        by_alias: bool | None = True,
        by_name: bool | None = False,
    ) -> Self:
        """
        Validate the given JSON data against the Pydantic model with auto-repair.

        Args:
            json_data: The JSON data to validate
            strict: Whether to enforce types strictly
            context: Extra variables to pass to the validator
            by_alias: Whether to use alias names for validation
            by_name: Whether field names should be matched by name

        Returns:
            The validated Pydantic model

        Raises:
            ValidationError: If the object could not be validated after repair
        """
        # Hide this function from tracebacks
        __tracebackhide__ = True
        kwargs = {
            "input": json_data,
            "strict": strict,
            "context": context,
            "by_alias": by_alias,
            "by_name": by_name,
        }

        try:
            return cls.__pydantic_validator__.validate_json(**kwargs)
        except RequestValidationError:
            if isinstance(json_data, str):
                json_str = json_data
            elif isinstance(json_data, (bytes, bytearray)):
                try:
                    json_str = json_data.decode("utf-8")
                except UnicodeDecodeError:
                    json_str = json_data.decode("utf-8", errors="ignore")
            elif isinstance(json_data, memoryview):
                raw = json_data.tobytes()
                try:
                    json_str = raw.decode("utf-8")
                except UnicodeDecodeError:
                    json_str = raw.decode("utf-8", errors="ignore")
            else:
                json_str = str(json_data)
            kwargs["input"] = repair_json(json_str)

        return cls.__pydantic_validator__.validate_json(**kwargs)


class SnowPlowModel(Model):
    """Base model for Snowplow data."""

    data: list[Any] = Field(...)
    json_schema: str | None = Field(
        None,
        alias="schema",
        title="Snowplow schema definition",
    )


class StructuredEvent(Model):
    """Model for structured events."""

    se_ac: str = Field(
        "",
        title="Event action",
        description="Only for event_type = se",
        validation_alias=AliasChoices("se_ac", "action"),
    )
    se_ca: str = Field(
        "",
        title="Event category",
        description="Only for event_type = se",
        validation_alias=AliasChoices("se_ca", "category"),
    )
    se_la: str = Field(
        "",
        title="Event label",
        description="Only for event_type = se",
        validation_alias=AliasChoices("se_la", "label"),
    )
    se_pr: str = Field(
        "",
        title="Event property",
        description="Only for event_type = se",
        validation_alias=AliasChoices("se_pr", "property"),
    )
    se_va: str = Field(
        "",
        title="Event value",
        description="Only for event_type = se",
        validation_alias=AliasChoices("se_va", "value"),
    )


class PayloadElementBaseModel(StructuredEvent):
    """Base model for payload elements (common to GET and POST)."""

    # URL and referrer fields
    url: str = Field("", title="Page URL")
    refr: str = Field("", title="Referrer URL")
    page: str = Field("", title="Page title")

    # Identifiers
    aid: str = Field(..., title="Unique identifier for website / application")
    eid: UUID | None = Field(None, title="Event UUID")
    duid: UUID | None = Field(
        None,
        title="Unique identifier for a user, based on a first party cookie",
    )
    uid: str = Field(
        "",
        title="Unique identifier for user, set by the business using setUserId",
    )
    sid: UUID | None = Field(
        None,
        title="Unique identifier (UUID) for this visit of this user_id to this domain",
    )
    vid: int = Field(
        0,
        title="Index of number of visits that this user_id has made to this domain",
    )

    # Event type and timestamps
    e: Literal["pv", "pp", "ue", "se", "tr", "ti"] = Field(
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
    p: str = Field(..., title="The platform the app runs on", description="ex. web")
    tv: str = Field(..., title="Identifier for Snowplow tracker")
    tna: str = Field("", title="The tracker namespace")
    tz: str | None = Field(None, title="Time zone of client device's OS")
    lang: str = Field("", title="Language the browser is set to")

    # Browser/viewport information
    cs: str = Field("", title="Web page's character encoding", description="ex. UTF-8")
    res: str = Field(..., title="Screen / monitor resolution")
    vp: str = Field("0x0", title="Browser viewport width and height")
    ds: str = Field("0x0", title="Web page width and height")
    cd: int = Field(0, title="Browser color depth")
    cookie: int | None = Field(None, title="Does the browser permit cookies?")

    # Page ping information (for pp event type)
    pp_mix: int = Field(0, title="Minimum page x offset seen in the last ping period")
    pp_max: int = Field(0, title="Maximum page x offset seen in the last ping period")
    pp_miy: int = Field(0, title="Minimum page y offset seen in the last ping period")
    pp_may: int = Field(0, title="Maximum page y offset seen in the last ping period")

    # Context information
    co: str | None = Field(None, title="An array of custom contexts")
    cx: str | None = Field(None, title="An array of custom contexts (b64)")

    # Unstructured event information
    ue_pr: str = Field("", title="The properties of the event")
    ue_px: str = Field("", title="The properties of the event (b64)")


class PayloadElementPostModel(PayloadElementBaseModel):
    """Model for POST payload elements with received timestamp."""

    rtm: datetime = Field(
        default_factory=lambda: datetime.now(),
        title="Timestamp when event was received by collector",
    )


class PayloadModel(SnowPlowModel):
    """Model for JSON payload in POST requests."""

    data: list[PayloadElementPostModel] = Field([])


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
