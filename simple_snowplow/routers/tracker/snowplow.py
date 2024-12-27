import base64
import urllib.parse as urlparse
from datetime import datetime
from http.cookies import SimpleCookie
from uuid import uuid4

import elasticapm
import orjson
import structlog
from config import settings
from routers.tracker import models

logger = structlog.stdlib.get_logger()


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
EMPTY_INTS = ()

payload_models = models.PayloadElementBaseModel | models.PayloadElementPostModel
schemas = settings.common.snowplow.schemas


@elasticapm.async_capture_span()
async def parse_base64(data: str | bytes, altchars=b"+/") -> str:
    if isinstance(data, str):
        data = data.encode("UTF-8")
    missing_padding = len(data) % 4
    if missing_padding:
        data += b"=" * (4 - missing_padding)

    return base64.urlsafe_b64decode(data).decode("UTF-8")


@elasticapm.async_capture_span()
async def parse_payload(element: payload_models, cookies: str) -> dict:
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

    # Post processing
    if element["aid"] == "undefined":
        element["aid"] = "other"
    if element["refr"] is not None:
        element["refr"] = urlparse.unquote(element["refr"])
    if element["e"] == "pp":
        element["extra"]["page_ping"] = {
            "min_x": element.pop("pp_mix"),
            "max_x": element.pop("pp_max"),
            "min_y": element.pop("pp_miy"),
            "max_y": element.pop("pp_may"),
        }

    # AMP specific
    if "uid" in element["amp"]:
        element["uid"] = element["amp"].pop("userId")
    if element["e"] == "ue" and "amp_page_ping" in element["ue"]:
        element["e"] = "pp"
        element["extra"]["amp_page_ping"] = element["ue"].pop("amp_page_ping")
    if "domainUserid" in element["amp"]:
        element["duid"] = element["amp"].pop("domainUserid")

    if element["url"] is not None:
        element["url"] = urlparse.unquote(element["url"])

    parsed_url = urlparse.urlparse(element["url"])
    query_string = urlparse.parse_qs(parsed_url.query)

    if query_string.get("sp_amp_linker", []):
        amp_linker = query_string["sp_amp_linker"][0]
        unknown_1, unknown_2, unknown_3, amp_device_id = amp_linker.split("*")
        amp_device_id = await parse_base64(amp_device_id)
        element["amp"]["device_id"] = amp_device_id

    if element["duid"] is None:
        sp_cookies = await parse_cookies(cookies)
        if sp_cookies:
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
                element["referer"] = ""
        else:
            element["referer"] = ""
        element["screen"] = dict(element["screen"], **element["ue"].pop("screen_view"))

    if "screen" in element and "screen_name" in element["screen"]:
        element["url"] = element["screen"].pop("screen_name")

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
            result["page_data"] = data
        elif schema == "com.snowplowanalytics.snowplow/mobile_context":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/mobile_context/jsonschema/1-0-3
            result["device_brand"] = data.pop("deviceManufacturer")
            result["device_model"] = data.pop("deviceModel")
            result["os_family"] = data.pop("osType")
            result["os_version_string"] = data.pop("osVersion")
            result["device_is"] = (1, 0, 1, 0, 0)
            result["device_extra"] = data
        elif schema == "com.snowplowanalytics.mobile/application":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/application/jsonschema/1-0-0
            # TODO: support for web
            result["app_version"] = data["version"]
            result["app_build"] = data["build"]
        elif schema == "com.snowplowanalytics.snowplow/client_session":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.snowplow/client_session/jsonschema/1-0-2
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
            result["user_data"] = data
        elif schema == schemas.ad_data:
            result["extra"]["ad_data"] = data
        elif schema == "com.snowplowanalytics.mobile/screen_summary":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/screen_summary/jsonschema/1-0-0
            result["extra"]["screen_summary"] = data
        elif schema == "com.snowplowanalytics.mobile/application_lifecycle":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.snowplowanalytics.mobile/application_lifecycle/jsonschema/1-0-0
            result["extra"]["app_lifecycle"] = data
        elif schema == "com.android.installreferrer.api/referrer_details":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/com.android.installreferrer.api/referrer_details/jsonschema/1-0-0
            result["extra"]["install_referrer"] = data
        elif schema == "org.w3/PerformanceNavigationTiming":
            # https://github.com/snowplow/iglu-central/blob/master/schemas/org.w3/PerformanceNavigationTiming/jsonschema/1-0-0
            result["extra"]["performance_navigation_timing"] = data
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
