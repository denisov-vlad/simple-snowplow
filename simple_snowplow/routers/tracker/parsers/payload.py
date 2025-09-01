"""
Payload parsing functionality for Snowplow events.
"""

import base64
import urllib.parse as urlparse
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Any
from uuid import UUID

import orjson
import structlog
from core.config import settings
from elasticapm.contrib.asyncio.traces import async_capture_span

from routers.tracker.models.snowplow import (
    PayloadElementBaseModel,
    PayloadElementPostModel,
    StructuredEvent,
)

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
    "duid",
    "sid",
    "view_id",
    "previous_session_id",
    "first_event_id",
)

DEFAULT_UUID = UUID("00000000-0000-0000-0000-000000000000")
DEFAULT_DATE = datetime(1970, 1, 1)

PayloadType = PayloadElementBaseModel | PayloadElementPostModel
schemas = settings.common.snowplow.schemas


@async_capture_span()
async def parse_base64(data: str | bytes, altchars: bytes = b"+/") -> str:
    """
    Parse base64 encoded data.

    Args:
        data: The base64 encoded data
        altchars: Alternative characters for base64 encoding

    Returns:
        Decoded string
    """

    if isinstance(data, str):
        data_bytes: bytes = data.encode("UTF-8")
    elif isinstance(data, (bytearray, memoryview)):
        data_bytes = bytes(data)
    else:
        data_bytes = data  # already bytes

    missing_padding = len(data_bytes) % 4
    if missing_padding:
        data_bytes = data_bytes + (b"=" * (4 - missing_padding))

    return base64.b64decode(data_bytes, altchars=altchars).decode("UTF-8")


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
            if len(parts) > 0:
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
async def parse_contexts(contexts: dict[str, Any]) -> dict[str, Any]:
    """
    Parse Snowplow contexts.

    Args:
        contexts: The contexts dictionary

    Returns:
        Processed contexts dictionary
    """
    result = {
        **{dict_name: {} for dict_name in EMPTY_DICTS},
        **{string_name: "" for string_name in EMPTY_STRINGS},
        **{date_name: DEFAULT_DATE for date_name in EMPTY_DATES},
        **{uuid_name: DEFAULT_UUID for uuid_name in EMPTY_UUIDS},
    }

    if not contexts or "data" not in contexts:
        return result

    for context in contexts["data"]:
        bad_contexts = False
        for key in ("schema", "data"):
            if not isinstance(context, dict):
                bad_contexts = True
                continue
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
                result["extra"][k] = v
        elif schema == "org.w3/PerformanceTiming":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/org.w3/PerformanceTiming/jsonschema/1-0-0
            result["extra"]["performance_timing"] = data
        elif schema == "org.ietf/http_client_hints":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/org.ietf/http_client_hints/jsonschema/1-0-0
            result["extra"]["client_hints"] = data
        elif schema in ("com.google.analytics/cookies", "com.google.ga4/cookies"):
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.google.analytics/cookies/jsonschema/1-0-0
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.google.ga4/cookies/jsonschema/1-0-0
            result["extra"]["ga_cookies"] = data
        elif schema == "com.snowplowanalytics.snowplow/web_page":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/web_page/jsonschema/1-0-0
            result["view_id"] = data["id"]
        elif schema in (
            "dev.amp.snowplow/amp_session",
            "dev.amp.snowplow/amp_id",
            "dev.amp.snowplow/amp_web_page",
        ):
            # https://github.com/snowplow/iglu-central/blob/master/schemas/dev.amp.snowplow/amp_session/jsonschema/1-0-0
            # https://github.com/snowplow/iglu-central/blob/master/schemas/dev.amp.snowplow/amp_id/jsonschema/1-0-0
            # https://github.com/snowplow/iglu-central/blob/master/schemas/dev.amp.snowplow/amp_web_page/jsonschema/1-0-0
            result["amp"] = dict(result["amp"], **data)
        elif schema == schemas.page_data:
            result["page_data"] = dict(result["page_data"], **data)
        elif schema == "com.snowplowanalytics.snowplow/mobile_context":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/mobile_context/jsonschema/1-0-3
            result["device_brand"] = data.pop("deviceManufacturer")
            result["device_model"] = data.pop("deviceModel")
            result["os_family"] = data.pop("osType")
            result["os_version_string"] = data.pop("osVersion")
            result["device_is_mobile"] = 1
            result["device_is_tablet"] = 0
            result["device_is_touch_capable"] = 1
            result["device_is_pc"] = 0
            result["device_is_bot"] = 0
            result["device_extra"] = data
        elif schema == "com.snowplowanalytics.mobile/application":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/application/jsonschema/1-0-0
            # TODO: support for web
            for k in ("version", "build"):
                if k in data and isinstance(data[k], str):
                    result[f"app_{k}"] = data[k]
        elif schema == "com.snowplowanalytics.snowplow/client_session":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/client_session/jsonschema/1-0-2
            visit_count = data.pop("sessionIndex", 0)
            if visit_count:
                result["vid"] = visit_count
            if data.get("sessionId"):
                result["sid"] = UUID(data.pop("sessionId"))
            if data.get("userId"):
                result["duid"] = UUID(data.pop("userId"))
            result["event_index"] = data.get("eventIndex", 0)
            first_event_time = data.get("firstEventTimestamp")
            if first_event_time is not None:
                result["first_event_time"] = datetime.fromisoformat(first_event_time)
            result["previous_session_id"] = data.get("previousSessionId", DEFAULT_UUID)
            result["first_event_id"] = data.get("firstEventId", DEFAULT_UUID)
            result["storage_mechanism"] = data.get("storageMechanism", "")
        elif schema == "com.snowplowanalytics.mobile/screen":
            # data is duplicated in event field is it's view
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/screen/jsonschema/1-0-0
            result["url"] = data.pop("name")
            result["view_id"] = data.pop("id")
            result["screen"] = dict(result["screen"], **data)
        elif schema == "com.snowplowanalytics.snowplow/browser_context":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/browser_context/jsonschema/2-0-0
            if "resolution" in data:
                result["res"] = data.pop("resolution")
            if "viewport" in data:
                result["vp"] = data.pop("viewport")
            if "documentSize" in data:
                result["ds"] = data.pop("documentSize")
            result["browser_extra"] = data
        elif schema == "com.snowplowanalytics.snowplow/geolocation_context":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/geolocation_context/jsonschema/1-1-0
            result["geolocation"] = data
        elif schema == schemas.screen_data:
            result["screen"] = dict(result["screen"], **data)
        elif schema == schemas.user_data:
            result["user_data"] = dict(result["user_data"], **data)

        # Unstructured events contexts
        elif schema == schemas.ad_data:
            result["ue_context"]["ad_data"] = data
        elif schema == "com.snowplowanalytics.mobile/screen_summary":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/screen_summary/jsonschema/1-0-0
            result["ue_context"]["screen_summary"] = data
        elif schema == "com.snowplowanalytics.mobile/application_lifecycle":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/application_lifecycle/jsonschema/1-0-0
            result["ue_context"]["app_lifecycle"] = data
        elif schema == "com.android.installreferrer.api/referrer_details":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.android.installreferrer.api/referrer_details/jsonschema/1-0-0
            result["ue_context"]["install_referrer"] = data
        elif schema == "org.w3/PerformanceNavigationTiming":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/org.w3/PerformanceNavigationTiming/jsonschema/1-0-0
            result["ue_context"]["performance_navigation_timing"] = data
        elif schema == "com.snowplowanalytics.mobile/deep_link_received":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/deep_link/jsonschema/1-0-0
            result["ue_context"]["deep_link_received"] = data
        elif schema == "com.snowplowanalytics.mobile/message_notification":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/message_notification/jsonschema/1-0-0
            result["ue_context"]["message_notification"] = data
        else:
            logger.warning("Schema has no parser", data=data, schema=schema)

    return result


@async_capture_span()
async def parse_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Parse Snowplow event data.

    Args:
        event: The event dictionary

    Returns:
        Processed event dictionary
    """
    event = event["data"]
    if event["schema"] == schemas.u2s_data:
        result = StructuredEvent.model_validate(event["data"]).model_dump()
        result["e"] = "se"
    else:
        event_name = event["schema"].split("/")[-3]
        result = {"ue": {event_name: event["data"]}}
    return result


@async_capture_span()
async def parse_payload(element: PayloadType, cookies: str | None) -> dict[str, Any]:
    """
    Parse a Snowplow event payload.

    Args:
        element: The payload element
        cookies: The cookies string

    Returns:
        Processed payload dictionary
    """
    element_dict = element.model_dump()
    # Explicit annotation so static type checkers allow heterogeneous values
    result: dict[str, Any] = {dict_name: {} for dict_name in EMPTY_DICTS}
    result.update(element_dict)

    # Process contexts
    context = None
    if element_dict.get("cx") is not None:
        context = element_dict.pop("cx")
        context = await parse_base64(context)
    elif element_dict.get("co") is not None:
        context = element_dict.pop("co")

    if context is not None:
        context = orjson.loads(context)
        parsed_context = await parse_contexts(context)
        result.update(parsed_context)

    # Process unstructured events
    event_context = None
    if element_dict.get("ue_px"):
        event_context = element_dict.pop("ue_px")
        event_context = await parse_base64(event_context)
    elif element_dict.get("ue_pr"):
        event_context = element_dict.pop("ue_pr")

    if event_context is not None:
        event_context = orjson.loads(event_context)
        event_data = await parse_event(event_context)
        result.update(event_data)
    else:
        result["ue"] = {}

    ue_context = result.pop("ue_context", {})
    if ue_context:
        result["ue"] = dict(result["ue"], **ue_context)

    # Handle page pings
    if result["e"] == "pp":
        result["extra"]["page_ping"] = {
            "min_x": result.pop("pp_mix", 0),
            "max_x": result.pop("pp_max", 0),
            "min_y": result.pop("pp_miy", 0),
            "max_y": result.pop("pp_may", 0),
        }

    # AMP-specific processing
    if "uid" in result.get("amp", {}):
        result["uid"] = result["amp"].pop("userId")
    if result["e"] == "ue" and "amp_page_ping" in result.get("ue", {}):
        result["e"] = "pp"
        result["extra"]["amp_page_ping"] = result["ue"].pop("amp_page_ping")
    if result.get("amp", {}).get("domainUserid"):
        result["duid"] = UUID(result["amp"].pop("domainUserid"))

    # Parse URL for AMP linker
    if result.get("url") and isinstance(result["url"], str):
        parsed_url = urlparse.urlparse(result["url"])
        query_string = urlparse.parse_qs(parsed_url.query)

        if query_string.get("sp_amp_linker", []):
            amp_linker = query_string["sp_amp_linker"][0]
            try:
                unknown_1, unknown_2, unknown_3, amp_device_id = amp_linker.split("*")
                amp_device_id = await parse_base64(amp_device_id)
                result["amp"]["device_id"] = amp_device_id
            except Exception as e:
                logger.warning(f"Failed to parse AMP linker: {e}")

    # Get cookie information if device ID is missing
    if result.get("duid") is None:
        sp_cookies = await parse_cookies(cookies)
        if sp_cookies and "device_id" in sp_cookies:
            result["duid"] = UUID(sp_cookies["device_id"])

    # Handle screen_view events
    if "screen_view" in result.get("ue", {}):
        result["e"] = "pv"
        result["view_id"] = result["ue"]["screen_view"].pop("id")
        result["url"] = result["ue"]["screen_view"].pop("name")

        if "previousName" in result["ue"]["screen_view"]:
            result["refr"] = result["ue"]["screen_view"].pop("previousName")
            if result["refr"] == "Unknown":
                result["refr"] = ""
        else:
            result["refr"] = ""

        result["screen"].update(result["ue"].pop("screen_view"))

    # Handle screen name in screen context
    if "screen" in result and "screen_name" in result["screen"]:
        result["url"] = result["screen"].pop("screen_name")

    # Parse structured event properties if they are JSON
    if result.get("se_pr") and isinstance(result["se_pr"], str):
        try:
            result["se_pr"] = orjson.loads(result["se_pr"])
        except (orjson.JSONDecodeError, TypeError):
            result["se_pr"] = {"ex-property": result["se_pr"]}
        finally:
            if not isinstance(result["se_pr"], dict):
                result["se_pr"] = {"ex-property": result["se_pr"]}
    else:
        result["se_pr"] = {}

    if "se_va" in result and result["se_va"]:
        if not isinstance(result["se_va"], (float, int)):
            try:
                result["se_va"] = float(result["se_va"])
            except ValueError:
                result["se_pr"]["ex-value"] = result["se_va"]
                result["se_va"] = 0.0
    else:
        result["se_va"] = 0.0

    is_mobile = result.get("extra", {}).get("client_hints", {}).get("isMobile")
    if is_mobile is not None:
        result["device_is_mobile"] = int(is_mobile)
        result["device_is_pc"] = int(not is_mobile)

    return result
