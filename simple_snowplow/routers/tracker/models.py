from datetime import datetime
from typing import Any
from typing import List

from fastapi import Query
from pydantic import AliasChoices
from pydantic import BaseModel
from pydantic import Field


class SnowPlowModel(BaseModel):
    data: List[Any | None] = Query(...)
    json_schema: str | None = Query(
        None,
        alias="schema",
        title="Snowplow schema definition",
    )


se_description = "Only for event_type = se"


class StructuredEvent(BaseModel):

    se_ac: str = Query(
        "",
        title="Event action",
        description=se_description,
        validation_alias=AliasChoices("se_ac", "action"),
    )
    se_ca: str = Query(
        "",
        title="Event category",
        description=se_description,
        validation_alias=AliasChoices("se_ca", "category"),
    )
    se_la: str = Query(
        "",
        title="Event label",
        description=se_description,
        validation_alias=AliasChoices("se_la", "label"),
    )
    se_pr: str = Query(
        "",
        title="Event property",
        description=se_description,
        validation_alias=AliasChoices("se_pr", "property"),
    )
    se_va: str = Query(
        "",
        title="Event value",
        description=se_description,
        validation_alias=AliasChoices("se_va", "value"),
    )


class PayloadElementBaseModel(StructuredEvent):
    # https://docs.snowplowanalytics.com/docs/collecting-data/collecting-from-own-applications/snowplow-tracker-protocol/
    aid: str = Query(..., title="Unique identifier for website / application")
    cd: int = Query(0, title="Browser color depth")
    cookie: int | None = Query(None, title="Does the browser permit cookies?")
    cs: str = Query("", title="Web page’s character encoding", description="ex. UTF-8")
    co: str | None = Query(None, title="An array of custom contexts (b64)")
    cx: str | None = Query(None, title="An array of custom contexts (b64)")
    ds: str = Query("0x0", title="Web page width and height")
    dtm: datetime = Field(
        default_factory=lambda: datetime.now(),
        title="Timestamp when event occurred, as recorded by client device",
    )
    duid: str | None = Query(
        None,
        title=(
            "Unique identifier for a user, based on a first party cookie "
            "(so domain specific)"
        ),
    )
    e: str = Query(
        ...,
        title="Event type",
        description="pv = page view, pp = page ping, ue = unstructured event, "
        "se = structured event, tr = transaction, ti = transaction item",
    )
    eid: str | None = Query(None, title="Event UUID")
    lang: str = Query("", title="Language the browser is set to")
    p: str = Query(..., title="The platform the app runs on", description="ex. web")
    page: str | None = Query(None, title="Page title")
    pp_mix: int = Query(0, title="Minimum page x offset seen in the last ping period")
    pp_max: int = Query(0, title="Maximum page x offset seen in the last ping period")
    pp_miy: int = Query(0, title="Minimum page y offset seen in the last ping period")
    pp_may: int = Query(0, title="Maximum page y offset seen in the last ping period")
    refr: str | None = Query(None, title="Referrer URL")
    res: str = Query(..., title="Screen / monitor resolution")
    sid: str | None = Query(
        None,
        title="Unique identifier (UUID) for this visit of this user_id to this domain",
    )
    stm: datetime | None = Field(
        default_factory=lambda: datetime.now(),
        title="Timestamp when event was sent by client device to collector",
    )
    tna: str = Query("", title="The tracker namespace")
    tv: str = Query(..., title="Identifier for Snowplow tracker")
    tz: str | None = Query(None, title="Time zone of client device’s OS")
    ue_pr: str = Query("", title="The properties of the event")
    ue_px: str = Query("", title="The properties of the event (b64)")
    uid: str | None = Query(
        None,
        title="Unique identifier for user, set by the business using setUserId",
    )
    url: str = Query("", title="Page URL")
    vid: int | None = Query(
        None,
        title="Index of number of visits that this user_id has made to this domain",
    )
    vp: str = Query("0x0", title="Browser viewport width and height")


class PayloadElementPostModel(PayloadElementBaseModel):
    rtm: datetime = Field(
        default_factory=lambda: datetime.now(),
        title="Timestamp when event was received by collector",
    )


class PayloadModel(SnowPlowModel):
    data: List[PayloadElementPostModel] = Query([])
