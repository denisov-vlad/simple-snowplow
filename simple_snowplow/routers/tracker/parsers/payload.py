"""
Payload parsing functionality for Snowplow events.
"""
import base64
import urllib.parse as urlparse
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Any
from typing import Dict
from typing import Optional
from typing import Union
from uuid import uuid4

import elasticapm
import orjson
import structlog
from config import settings
from routers.tracker.schemas.models import PayloadElementBaseModel
from routers.tracker.schemas.models import PayloadElementPostModel

logger = structlog.stdlib.get_logger()

# Constants for empty values
EMPTY_DICTS = (
    "extra",
    "user_data",
    "page_data",
    "screen",
    "session_unstructured",
    "browser_extra",
    "amp",
    "device_extra",
)
EMPTY_STRINGS = (
    "app_version",
    "app_build",
    "storage_mechanism",
    "device_model",
    "device_brand",
)

PayloadType = Union[PayloadElementBaseModel, PayloadElementPostModel]
schemas = settings.common.snowplow.schemas


@elasticapm.async_capture_span()
async def parse_base64(data: Union[str, bytes], altchars: bytes = b"+/") -> str:
    """
    Parse base64 encoded data.

    Args:
        data: The base64 encoded data
        altchars: Alternative characters for base64 encoding

    Returns:
        Decoded string
    """
    if isinstance(data, str):
        data = data.encode("UTF-8")
    missing_padding = len(data) % 4
    if missing_padding:
        data += b"=" * (4 - missing_padding)

    return base64.urlsafe_b64decode(data).decode("UTF-8")


@elasticapm.async_capture_span()
async def parse_cookies(cookies_str: Optional[str]) -> Dict[str, Any]:
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

        # Extract session ID from sp cookie
        if name.startswith("_sp_ses"):
            result["session_id"] = cookie.value

    return result


@elasticapm.async_capture_span()
async def parse_contexts(contexts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Snowplow contexts.

    Args:
        contexts: The contexts dictionary

    Returns:
        Processed contexts dictionary
    """
    result = {dict_name: {} for dict_name in EMPTY_DICTS}
    result.update({string_name: "" for string_name in EMPTY_STRINGS})

    if not contexts or "data" not in contexts:
        return result

    for context in contexts.get("data", []):
        # Skip invalid contexts
        if (
            not isinstance(context, dict)
            or "schema" not in context
            or "data" not in context
        ):
            continue

        schema = context["schema"]
        data = context["data"]

        # Process different context types based on schema
        if schemas.session in schema:
            result["event_index"] = data.get("eventIndex")
            result["previous_session_id"] = data.get("previousSessionId")
            result["first_event_id"] = data.get("firstEventId")
            result["first_event_time"] = data.get("firstEventTimestamp")
            result["storage_mechanism"] = data.get("storageMechanism", "")
            result["session_unstructured"] = data

        elif schemas.webpage in schema:
            if data.get("referrer"):
                result["refr"] = data["referrer"]
            result["page_data"] = data

        elif schemas.user in schema:
            result["user_data"] = data

        elif schemas.screen in schema:
            result["screen"] = data

        elif schemas.amp in schema:
            result["amp"] = data

        elif schemas.client in schema:
            # Process client-specific data
            result["browser_extra"] = data.get("browser", {})
            if "deviceType" in data:
                result["device_extra"]["type"] = data["deviceType"]

            result["lang"] = data.get("language", "")

            if "mobile" in data:
                result["device_is"] = (
                    data["mobile"].get("deviceClass") == "Mobile",
                    data["mobile"].get("deviceClass") == "Tablet",
                    data["mobile"].get("touchCapable", False),
                    not data["mobile"].get("touchCapable", False),
                    False,
                )

        # Add any other contexts to extra
        elif "schema" in context and "data" in context:
            schema_name = schema.split("/")[-1].split("-")[0]
            result["extra"][schema_name] = data

    return result


@elasticapm.async_capture_span()
async def parse_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Snowplow event data.

    Args:
        event: The event dictionary

    Returns:
        Processed event dictionary
    """
    result = {"ue": {}}

    if not event or "schema" not in event or "data" not in event:
        return result

    schema = event["schema"]
    data = event["data"]

    # Extract schema name
    schema_name = schema.split("/")[-1].split("-")[0]
    result["ue"][schema_name] = data

    return result


@elasticapm.async_capture_span()
async def parse_payload(element: PayloadType, cookies: Optional[str]) -> Dict[str, Any]:
    """
    Parse a Snowplow event payload.

    Args:
        element: The payload element
        cookies: The cookies string

    Returns:
        Processed payload dictionary
    """
    element_dict = element.model_dump()
    result = {dict_name: {} for dict_name in EMPTY_DICTS}
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

    # Set timestamps
    if result.get("rtm") is None:
        result["rtm"] = datetime.now()
    if result.get("stm") is None:
        result["stm"] = datetime.now()

    # Post processing
    if result["aid"] == "undefined":
        result["aid"] = "other"

    # Decode URL-encoded fields
    if result.get("refr"):
        result["refr"] = urlparse.unquote(result["refr"])
    if result.get("url"):
        result["url"] = urlparse.unquote(result["url"])

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
    if "domainUserid" in result.get("amp", {}):
        result["duid"] = result["amp"].pop("domainUserid")

    # Parse URL for AMP linker
    if result.get("url"):
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
            result["duid"] = sp_cookies["device_id"]

    # Truncate UUIDs if they're too long
    for uid in ("duid", "sid", "view_id"):
        if (
            result.get(uid) is not None
            and isinstance(result[uid], str)
            and len(result[uid]) > 36
        ):
            result[uid] = result[uid][:36]

    # Generate event ID if missing
    if result.get("eid") is None:
        result["eid"] = str(uuid4())

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
    if "se_pr" in result and result["se_pr"]:
        try:
            result["se_pr"] = orjson.loads(result["se_pr"])
        except (orjson.JSONDecodeError, TypeError):
            pass

    return result
