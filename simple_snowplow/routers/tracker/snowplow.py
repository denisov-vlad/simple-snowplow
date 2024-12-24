import base64
import urllib.parse as urlparse
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Union
from uuid import uuid4

import elasticapm
import orjson
import structlog
from config import settings
from inflection import underscore
from routers.tracker import models

logger = structlog.stdlib.get_logger()


EMPTY_DICTS = (
    "extra",
    "user_data",
    "page_data",
    "screen_unstructured",
    "session_unstructured",
    "browser_unstructured",
)
EMPTY_STRINGS = (
    "app_version",
    "app_build",
    "storage_mechanism",
    "screen_type",
    "screen_vc",
    "screen_tvc",
    "screen_activity",
    "screen_fragment",
    "device_model",
    "device_brand",
    "carrier",
    "network_type",
    "network_technology",
    "open_idfa",
    "apple_idfa",
    "apple_idfv",
    "android_idfa",
    "battery_state",
    "amp_device_id",
    "amp_client_id",
    "amp_view_id",
)
EMPTY_INTS = (
    "amp_session_id",
    "amp_visit_count",
    "amp_session_engaged",
    "battery_level",
    "low_power_mode",
)

schemas = settings.common.snowplow.schemas


@elasticapm.async_capture_span()
async def parse_base64(data: Union[str, bytes], altchars=b"+/") -> str:
    if isinstance(data, str):
        data = data.encode("UTF-8")
    missing_padding = len(data) % 4
    if missing_padding:
        data += b"=" * (4 - missing_padding)

    return base64.urlsafe_b64decode(data).decode("UTF-8")


@elasticapm.async_capture_span()
async def parse_payload(
    element: Union[models.PayloadElementBaseModel, models.PayloadElementPostModel],
    cookies: str,
) -> dict:
    element = element.model_dump()

    context = None
    if element["cx"] is not None:
        context = element.pop("cx")
        context = await parse_base64(context)
    elif element["co"] is not None:
        context = element.pop("co")

    if context is not None:
        context = orjson.loads(context)
        parsed_context = await parse_contexts(context)
        element = dict(element, **parsed_context)

    event_context = None
    if element["ue_px"]:
        event_context = element.pop("ue_px")
        event_context = await parse_base64(event_context)
    elif element["ue_pr"]:
        event_context = element.pop("ue_pr")

    if event_context is not None:
        event_context = orjson.loads(event_context)
        event_data = await parse_event(event_context)
        for k, v in event_data.items():
            element[k] = v
    else:
        element["ue"] = {}

    if element.get("rtm") is None:
        element["rtm"] = datetime.now()

    if element.get("stm") is None:
        element["stm"] = datetime.now()

    if element.get("cookie") is None:
        if cookies:
            element["cookie"] = 1
        else:
            element["cookie"] = 0

    # Post processing
    if element["aid"] == "undefined":
        element["aid"] = "other"
    if element["refr"] is not None:
        element["refr"] = urlparse.unquote(element["refr"])
    for key in ("refr", "uid"):
        if element[key] == "":
            element[key] = None
    if element["e"] == "pp":
        element["extra"]["page_ping"] = {
            "min_x": element.pop("pp_mix"),
            "max_x": element.pop("pp_max"),
            "min_y": element.pop("pp_miy"),
            "max_y": element.pop("pp_may"),
        }

    # AMP specific
    if element.get("amp_uid", ""):
        element["uid"] = element["amp_uid"]
    if element["e"] == "ue" and "amp_page_ping" in element["ue"]:
        element["e"] = "pp"
        element["extra"]["amp_page_ping"] = element["ue"].pop("amp_page_ping")

    if element["url"] is not None:
        element["url"] = urlparse.unquote(element["url"])

    parsed_url = urlparse.urlparse(element["url"])
    query_string = urlparse.parse_qs(parsed_url.query)

    if query_string.get("sp_amp_linker", []):
        amp_linker = query_string["sp_amp_linker"][0]
        unknown_1, unknown_2, unknown_3, amp_device_id = amp_linker.split("*")
        amp_device_id = await parse_base64(amp_device_id)
        element["amp_device_id"] = amp_device_id

    sp_cookies = await parse_cookies(cookies)
    if sp_cookies:
        if element["duid"] is None:
            element["duid"] = sp_cookies["device_id"]

    for uid in ("duid", "sid", "view_id"):
        if element.get(uid) is not None and len(element[uid]) > 36:
            element[uid] = element[uid][:36]

    if element["eid"] is None:
        element["eid"] = uuid4()

    if "screen_view" in element.get("ue", {}):
        element["e"] = "pv"
        element["view_id"] = element["ue"]["screen_view"].pop("id")
        element["url"] = element["ue"]["screen_view"].pop("name")
        if "previousName" in element["ue"]["screen_view"]:
            element["referer"] = element["ue"]["screen_view"].pop("previousName")
            if element["referer"] == "Unknown":
                element["referer"] = None
        else:
            element["referer"] = None
        for k, v in element["ue"]["screen_view"].items():
            element["screen_unstructured"][underscore(k)] = v
        _ = element["ue"].pop("screen_view")

    if (
        "screen_unstructured" in element
        and "screen_name" in element["screen_unstructured"]
    ):
        element["url"] = element["screen_unstructured"].pop("screen_name")

    if "se_pr" in element and element["se_pr"]:
        try:
            element["se_pr"] = orjson.loads(element["se_pr"])
            if not isinstance(element["se_pr"], dict):
                element["se_pr"] = {}
        except orjson.JSONDecodeError:
            element["se_pr"] = {"ex-property": element["se_pr"]}
    else:
        element["se_pr"] = {}

    if "se_va" in element and element["se_va"]:
        if not isinstance(element["se_va"], (float, int)):
            try:
                element["se_va"] = float(element["se_va"])
            except ValueError:
                element["se_pr"]["ex-value"] = element["se_va"]
                element["se_va"] = 0.0
    else:
        element["se_va"] = 0.0

    return element


@elasticapm.async_capture_span()
async def parse_contexts(contexts: dict) -> dict:
    result = {}
    for col in EMPTY_DICTS:
        result[col] = {}
    for col in EMPTY_STRINGS:
        result[col] = ""
    for col in EMPTY_INTS:
        result[col] = 0

    for item in contexts["data"]:
        if "schema" not in item:
            await logger.warning("Empty schema for payload", item=item)
            continue

        schema = "/".join(item["schema"][5:].split("/")[:2])
        data = item["data"]

        if not isinstance(data, dict):
            await logger.warning("Wrong data type", data=data)
            continue

        if schema == "com.acme/static_context":
            for k, v in item["data"].items():
                result["extra"][k] = v
        elif schema == "org.w3/PerformanceTiming":
            result["extra"]["performance_timing"] = item["data"]
        elif schema == "org.ietf/http_client_hints":
            result["extra"]["client_hints"] = item["data"]
        elif schema in ("com.google.analytics/cookies", "com.google.ga4/cookies"):
            result["extra"]["ga_cookies"] = item["data"]
        elif schema == "com.snowplowanalytics.snowplow/web_page":
            result["view_id"] = item["data"]["id"]
        elif schema == "dev.amp.snowplow/amp_session":
            if "ampSessionId" in data:
                result["amp_session_id"] = data["ampSessionId"]
            if "sessionCreationTimestamp" in data:
                result["amp_first_event_time"] = data["sessionCreationTimestamp"]
            if "lastSessionEventTimestamp" in data:
                result["amp_previous_session_time"] = data["sessionCreationTimestamp"]
            if "sessionEngaged" in data:
                result["amp_session_engaged"] = data["sessionEngaged"]
            if "ampSessionIndex" in data:
                result["amp_visit_count"] = data["ampSessionIndex"]
        elif schema == "dev.amp.snowplow/amp_id":
            result["amp_client_id"] = data["ampClientId"]
            result["amp_device_id"] = data.get("domainUserid", "")
            result["amp_uid"] = data.get("userId", "")
        elif schema == "dev.amp.snowplow/amp_web_page":
            result["amp_view_id"] = item["data"]["ampPageViewId"]
        elif schema == schemas.page_data:
            result["page_data"] = item["data"]
        elif schema == "com.snowplowanalytics.snowplow/mobile_context":
            result["device_brand"] = data.pop("deviceManufacturer")
            result["device_model"] = data.pop("deviceModel")
            result["os_family"] = data.pop("osType")
            result["os_version_string"] = data.pop("osVersion")
            result["device_is"] = (1, 0, 1, 0, 0)
            result["carrier"] = data.get("carrier", "")
            result["network_type"] = data.get("networkType", "")
            result["network_technology"] = data.get("networkTechnology", "")
            result["open_idfa"] = data.get("openIdfa", "")
            result["apple_idfa"] = data.get("appleIdfa", "")
            result["apple_idfv"] = data.get("appleIdfv", "")
            result["android_idfa"] = data.get("androidIdfa", "")
            result["battery_level"] = data.get("batteryLevel", 0)
            result["battery_state"] = data.get("batteryState", "")
            result["low_power_mode"] = data.get("lowPowerMode", False)
        elif schema == "com.snowplowanalytics.mobile/application":
            result["app_version"] = item["data"]["version"]
            result["app_build"] = item["data"]["build"]
        elif schema == "com.snowplowanalytics.snowplow/client_session":
            result["vid"] = data.pop("sessionIndex")
            result["sid"] = data.pop("sessionId")
            result["duid"] = data.pop("userId")
            result["event_index"] = data.get("eventIndex")
            first_event_time = data.get("firstEventTimestamp")
            if first_event_time is not None:
                result["first_event_time"] = datetime.fromisoformat(first_event_time)
            result["previous_session_id"] = data.get("previousSessionId", "")
            result["first_event_id"] = data.get("firstEventId", "")
            result["storage_mechanism"] = data.get("storageMechanism", "")
        elif schema == "com.snowplowanalytics.mobile/screen":
            # data is duplicated in event field is it's view
            result["url"] = data.pop("name")
            result["view_id"] = data.pop("id")
            result["screen_type"] = data.get("type", "")
            result["screen_vc"] = data.get("viewController", "")
            result["screen_tvc"] = data.get("topViewController", "")
            result["screen_activity"] = data.get("activity", "")
            result["screen_fragment"] = data.get("fragment", "")
        elif schema == "com.snowplowanalytics.snowplow/browser_context":
            if "cookiesEnabled" in data:
                result["cookie"] = data.pop("cookiesEnabled")
            if "documentSize" in data:
                result["ds"] = data.pop("documentSize")
            if "viewport" in data:
                result["vp"] = data.pop("viewport")
            if "resolution" in data:
                result["res"] = data.pop("resolution")
            if "colorDepth" in data:
                result["cd"] = data.pop("colorDepth")
            if "browserLanguage" in data:
                result["lang"] = data.pop("browserLanguage")
            result["browser_unstructured"] = data
        elif schema == "com.snowplowanalytics.snowplow/geolocation_context":
            geo_data = {k: v for k, v in data.items() if v is not None}
            result["geolocation"] = geo_data
        elif schema == schemas.screen_data:
            if "screen_unstructured" not in result:
                result["screen_unstructured"] = {}
            for k, v in data.items():
                result["screen_unstructured"][k] = v
        elif schema == schemas.user_data:
            for k, v in data.items():
                result["user_data"][k] = v
        elif schema == schemas.ad_data:
            result["extra"]["ad_data"] = item["data"]
        elif schema == "com.snowplowanalytics.mobile/application_lifecycle":
            result["extra"]["app_lifecycle"] = item["data"]
        elif schema == "com.android.installreferrer.api/referrer_details":
            result["extra"]["install_referrer"] = item["data"]
        elif schema == "org.w3/PerformanceNavigationTiming":
            result["extra"]["performance_navigation_timing"] = item["data"]
        elif schema == "com.snowplowanalytics.mobile/screen_summary":
            if "screen_unstructured" not in result:
                result["screen_unstructured"] = {}
            for k, v in data.items():
                result["screen_unstructured"][k] = v
        else:
            await logger.warning("Schema has no parser", data=data, schema=schema)

    return result


@elasticapm.async_capture_span()
async def parse_event(event: dict) -> dict:
    event = event["data"]
    if event["schema"] == schemas.u2s_data:
        result = models.StructuredEvent.model_validate(event["data"]).model_dump()
        result["e"] = "se"
    else:
        event_name = event["schema"].split("/")[-3]
        result = {"ue": {event_name: event["data"]}}
    return result


@elasticapm.async_capture_span()
async def parse_cookies(cookies_str: str) -> dict:
    result = {}

    if cookies_str is None:
        return result

    cookies_dict: SimpleCookie = SimpleCookie()
    cookies_dict.load(cookies_str)

    if cookies_dict:
        cookie_value = None
        for k, v in cookies_dict.items():
            if k.startswith("_sp_id."):
                cookie_value = v.value
                break

        if cookie_value:
            cookie_value_list = cookie_value.split(".")
            result["device_id"] = cookie_value_list[0]
            result["created_time"] = cookie_value_list[1]
            result["visit_count"] = cookie_value_list[2]
            result["now_time"] = cookie_value_list[3]
            result["last_visit_time"] = cookie_value_list[4]
            result["session_id"] = cookie_value_list[5]

    return result
