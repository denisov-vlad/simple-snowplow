"""
Payload parsing functionality for Snowplow events.
"""

import urllib.parse as urlparse
from datetime import datetime
from http.cookies import SimpleCookie
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

import orjson
import structlog
from core.config import settings
from elasticapm.contrib.asyncio.traces import async_capture_span
from routers.tracker.models.snowplow import (
    InsertModel,
    PayloadElementModel,
    StructuredEvent,
    UserAgentModel,
)
from routers.tracker.parsers.utils import parse_base64

logger = structlog.stdlib.get_logger()

# Constants for empty values
EMPTY_DICTS = (
    "ue_context",
    "extra",
    "user_data",
    "page_data",
    "screen",
    "session_unstructured",
    "browser_extra",
    "amp",
    "device_extra",
    "geolocation",
)
EMPTY_STRINGS = (
    "app_version",
    "app_build",
    "storage_mechanism",
    "device_model",
    "device_brand",
)

EMPTY_DATES = ("first_event_time",)

EMPTY_UUIDS = (
    "view_id",
    "previous_session_id",
    "first_event_id",
)

EMPTY_INTS = ("event_index",)

DEFAULT_UUID = UUID("00000000-0000-0000-0000-000000000000")
DEFAULT_DATE = datetime(1970, 1, 1)

schemas = settings.common.snowplow.schemas


@async_capture_span()
async def parse_cookies(cookies_str: str | None) -> dict[str, Any]:
    """
    Parse cookies string.

    Args:
        cookies_str: The cookies string

    Returns:
        Dictionary of cookie values
    """
    if not cookies_str:
        return {}

    cookies = SimpleCookie()
    try:
        cookies.load(cookies_str)
    except Exception as e:
        logger.warning(f"Failed to parse cookies: {e}")
        return {}

    # Extract Snowplow specific cookies
    result = {}
    for name, cookie in cookies.items():
        # Extract domain user ID from sp cookie
        if name.startswith("_sp_id"):
            parts = cookie.value.split(".")
            if len(parts) < 6:
                logger.warning("Incomplete _sp_id cookie", cookie_value=cookie.value)
                continue

            result["device_id"] = parts[0]
            result["created_time"] = parts[1]
            if parts[2] is not None:
                result["vid"] = parts[2]
            result["now_time"] = parts[3]
            result["last_visit_time"] = parts[4]
            result["session_id"] = parts[5]

        # # Extract session ID from sp cookie
        # if name.startswith("_sp_ses"):
        #     result["session_id"] = cookie.value

    return result


@async_capture_span()
async def parse_contexts(
    contexts: dict[str, Any] | None,
    model: InsertModel,
) -> InsertModel:
    """
    Parse Snowplow contexts.

    Args:
        contexts: The contexts dictionary
        model: The InsertModel to update

    Returns:
        Processed InsertModel with updated fields
    """

    if not contexts or "data" not in contexts:
        return model

    for context in contexts["data"]:
        bad_contexts = False
        if not isinstance(context, dict):
            bad_contexts = True
            continue
        for key in ("schema", "data"):
            if key not in context:
                logger.warning(f"Empty {key} for payload", context=context)
                continue

        if bad_contexts:
            logger.error("Bad contexts", contexts=contexts)
            continue

        schema = "/".join(context["schema"][5:].split("/")[:2])
        data = context["data"]

        if not isinstance(data, dict):
            logger.warning("Wrong data type", context=context)
            continue

        # Process different context types based on schema
        if schema == "com.acme/static_context":
            for k, v in data.items():
                model.extra[k] = v
        elif schema == "org.w3/PerformanceTiming":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/org.w3/PerformanceTiming/jsonschema/1-0-0
            model.extra["performance_timing"] = data
        elif schema == "org.ietf/http_client_hints":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/org.ietf/http_client_hints/jsonschema/1-0-0
            model.extra["client_hints"] = data
        elif schema in ("com.google.analytics/cookies", "com.google.ga4/cookies"):
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.google.analytics/cookies/jsonschema/1-0-0
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.google.ga4/cookies/jsonschema/1-0-0
            model.extra["ga_cookies"] = data
        elif schema == "com.snowplowanalytics.snowplow/web_page":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/web_page/jsonschema/1-0-0
            model.view_id = UUID(data["id"])
        elif schema in (
            "dev.amp.snowplow/amp_session",
            "dev.amp.snowplow/amp_id",
            "dev.amp.snowplow/amp_web_page",
        ):
            # https://github.com/snowplow/iglu-central/blob/master/schemas/dev.amp.snowplow/amp_session/jsonschema/1-0-0
            # https://github.com/snowplow/iglu-central/blob/master/schemas/dev.amp.snowplow/amp_id/jsonschema/1-0-0
            # https://github.com/snowplow/iglu-central/blob/master/schemas/dev.amp.snowplow/amp_web_page/jsonschema/1-0-0
            model.amp = dict(model.amp, **data)
        elif schema == schemas.page_data:
            model.page_data = dict(model.page_data, **data)
        elif schema == "com.snowplowanalytics.snowplow/mobile_context":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/mobile_context/jsonschema/1-0-3
            model.device_brand = data.pop("deviceManufacturer")
            model.device_model = data.pop("deviceModel")
            model.os_family = data.pop("osType")
            model.os_version_string = data.pop("osVersion")
            model.device_is_mobile = True
            model.device_is_touch_capable = True
            model.device_extra = data
        elif schema == "com.snowplowanalytics.mobile/application":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/application/jsonschema/1-0-0
            # TODO: support for web
            for k in ("version", "build"):
                if k in data and isinstance(data[k], str):
                    setattr(model, f"app_{k}", data[k])
        elif schema == "com.snowplowanalytics.snowplow/client_session":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/client_session/jsonschema/1-0-2
            visit_count = data.pop("sessionIndex", 0)
            if visit_count:
                model.vid = visit_count
            if data.get("sessionId"):
                model.sid = UUID(data.pop("sessionId"))
            if data.get("userId"):
                model.duid = UUID(data.pop("userId"))
            model.event_index = data.pop("eventIndex", 0)
            first_event_time = data.pop("firstEventTimestamp", None)
            if first_event_time is not None:
                model.first_event_time = datetime.fromisoformat(first_event_time)
            previous_session_id = data.pop("previousSessionId", None)
            if previous_session_id:
                model.previous_session_id = UUID(previous_session_id)
            first_event_id = data.pop("firstEventId", None)
            if first_event_id:
                model.first_event_id = UUID(first_event_id)
            model.storage_mechanism = data.pop("storageMechanism", "")
        elif schema == "com.snowplowanalytics.mobile/screen":
            # data is duplicated in event field is it's view
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/screen/jsonschema/1-0-0
            model.url = data.pop("name")
            model.view_id = UUID(data.pop("id"))
            model.screen = dict(model.screen, **data)
        elif schema == "com.snowplowanalytics.snowplow/browser_context":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/browser_context/jsonschema/2-0-0
            if "resolution" in data:
                model.res = data.pop("resolution")
            if "viewport" in data:
                model.vp = data.pop("viewport")
            if "documentSize" in data:
                model.ds = data.pop("documentSize")
            if data:
                model.browser_extra = data
        elif schema == "com.snowplowanalytics.snowplow/geolocation_context":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/geolocation_context/jsonschema/1-1-0
            model.geolocation = data
        elif schema == schemas.screen_data:
            model.screen = dict(model.screen, **data)
        elif schema == schemas.user_data:
            model.user_data = dict(model.user_data, **data)

        # Unstructured events contexts
        elif schema == schemas.ad_data:
            model.ue["ad_data"] = data
        elif schema == "com.snowplowanalytics.mobile/screen_summary":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/screen_summary/jsonschema/1-0-0
            model.ue["screen_summary"] = data
        elif schema == "com.snowplowanalytics.mobile/application_lifecycle":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/application_lifecycle/jsonschema/1-0-0
            model.ue["app_lifecycle"] = data
        elif schema == "com.android.installreferrer.api/referrer_details":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.android.installreferrer.api/referrer_details/jsonschema/1-0-0
            model.ue["install_referrer"] = data
        elif schema == "org.w3/PerformanceNavigationTiming":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/org.w3/PerformanceNavigationTiming/jsonschema/1-0-0
            model.ue["performance_navigation_timing"] = data
        elif schema == "com.snowplowanalytics.mobile/deep_link_received":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/deep_link/jsonschema/1-0-0
            model.ue["deep_link_received"] = data
        elif schema == "com.snowplowanalytics.mobile/message_notification":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/message_notification/jsonschema/1-0-0
            model.ue["message_notification"] = data
        else:
            logger.warning("Schema has no parser", data=data, schema=schema)

    return model


@async_capture_span()
async def parse_event(event: dict[str, Any] | None, model: InsertModel) -> InsertModel:
    """
    Parse Snowplow event data.

    Args:
        event: The event dictionary
        model: The InsertModel to update

    Returns:
        Processed InsertModel with updated fields
    """

    if event is None or "data" not in event:
        return model

    event_payload: dict[str, Any] = event["data"]
    if event_payload["schema"] == schemas.u2s_data:
        se = StructuredEvent.model_validate(event_payload["data"])
        for field_name in StructuredEvent.model_fields:
            setattr(model, field_name, getattr(se, field_name))
        model.e = "se"
    else:
        event_name = event_payload["schema"].split("/")[-3]
        model.ue[event_name] = event_payload["data"]
    return model


@async_capture_span()
async def parse_payload(
    element: PayloadElementModel,
    user_agent: UserAgentModel,
    ip: IPv4Address,
    cookies: str | None,
) -> InsertModel:
    """
    Parse a Snowplow event payload.

    Args:
        element: The payload element
        user_agent: The parsed user agent data
        ip: The user's IP address
        cookies: The cookies string

    Returns:
        Processed InsertModel with all data combined
    """

    data = element.model_dump()
    ua_data = user_agent.model_dump()
    data = {**ua_data, **data, "user_ip": ip}

    result = InsertModel.model_validate(data)
    result = await parse_contexts(element.contexts, result)
    result = await parse_event(element.ue_context, result)

    if element.ping_context:
        result.ue["page_ping"] = element.ping_context

    # AMP-specific processing
    if "uid" in result.amp:
        result.uid = result.amp.pop("userId")
    if result.e == "ue" and "amp_page_ping" in result.ue:
        result.e = "pp"
        result.ue["amp_page_ping"] = result.ue.pop("amp_page_ping")
    if result.amp.get("domainUserid"):
        result.duid = UUID(result.amp.pop("domainUserid"))

    # Parse URL for AMP linker
    if result.url:
        parsed_url = urlparse.urlparse(result.url)
        query_string = urlparse.parse_qs(parsed_url.query)

        if query_string.get("sp_amp_linker", []):
            amp_linker = query_string["sp_amp_linker"][0]
            try:
                unknown_1, unknown_2, unknown_3, amp_device_id = amp_linker.split("*")
                amp_device_id = parse_base64(amp_device_id)
                result.amp["device_id"] = UUID(amp_device_id)
            except Exception as e:
                logger.warning(f"Failed to parse AMP linker: {e}")

    # Get cookie information if device ID is missing
    if result.duid is None:
        sp_cookies = await parse_cookies(cookies)
        if sp_cookies and "device_id" in sp_cookies:
            result.duid = UUID(sp_cookies["device_id"])

    # Handle screen_view events
    if "screen_view" in result.ue:
        result.e = "pv"
        result.view_id = UUID(result.ue["screen_view"].pop("id"))
        result.url = result.ue["screen_view"].pop("name")

        if "previousName" in result.ue["screen_view"]:
            result.refr = result.ue["screen_view"].pop("previousName")
            if result.refr == "Unknown":
                result.refr = ""
        else:
            result.refr = ""

        result.screen.update(result.ue.pop("screen_view"))

    # Handle screen name in screen context
    if "screen_name" in result.screen:
        result.url = result.screen.pop("screen_name")

    # Parse structured event properties if they are JSON
    if result.se_pr and isinstance(result.se_pr, str):
        try:
            result.se_pr = orjson.loads(result.se_pr)
        except (orjson.JSONDecodeError, TypeError):
            result.se_pr = {"ex-property": result.se_pr}
        finally:
            if not isinstance(result.se_pr, dict):
                result.se_pr = {"ex-property": result.se_pr}
    else:
        result.se_pr = {}

    if result.se_va:
        if not isinstance(result.se_va, (float, int)):
            try:
                result.se_va = float(result.se_va)
            except ValueError:
                result.se_pr["ex-value"] = result.se_va
                result.se_va = 0.0
    else:
        result.se_va = 0.0

    is_mobile = result.extra.get("client_hints", {}).get("isMobile")
    if is_mobile is not None:
        result.device_is_mobile = bool(int(is_mobile))
        result.device_is_pc = bool(int(not is_mobile))

    return result
