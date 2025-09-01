"""
Data models for Snowplow events.
"""

import urllib.parse as urlparse
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import AliasChoices, Field, field_validator

from .base import Model


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
    eid: UUID = Field(default_factory=lambda: uuid4(), title="Event UUID")
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
    e: Literal["pv", "pp", "ue", "se", "tr", "ti", "s"] = Field(
        ...,
        title="Event type",
        description="pv = page view, pp = page ping, ue = unstructured event, "
        "se = structured event, tr = transaction, ti = transaction item, s = session",
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
    p: Literal["web", "mob", "pc", "srv", "app", "tv", "cnsl", "iot"] = Field(
        ...,
        title="The platform the app runs on",
        description="i.e. web",
    )
    tv: str = Field(..., title="Identifier for Snowplow tracker")
    tna: str = Field("", title="The tracker namespace")
    tz: str | None = Field(None, title="Time zone of client device's OS")
    lang: str = Field("", title="Language the browser is set to")

    # Browser/viewport information
    cs: str = Field("", title="Web page's character encoding", description="i.e. UTF-8")
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

    @field_validator("aid", mode="before")
    @classmethod
    def rename_aid(cls, v):
        if v == "undefined":
            return "other"
        return v

    @field_validator("refr", "url", mode="before")
    @classmethod
    def decode_url_fields(cls, v):
        return urlparse.unquote(v) if v else v


class PayloadElementPostModel(PayloadElementBaseModel):
    """Model for POST payload elements with received timestamp."""

    rtm: datetime = Field(
        default_factory=lambda: datetime.now(),
        title="Timestamp when event was received by collector",
    )


class PayloadModel(SnowPlowModel):
    """Model for JSON payload in POST requests."""

    data: list[PayloadElementPostModel] = Field([])
