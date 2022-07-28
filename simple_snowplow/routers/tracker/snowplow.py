import base64
import re
import urllib.parse as urlparse
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Union
from uuid import uuid4

import elasticapm
import orjson
from inflection import underscore
from routers.tracker import models


@elasticapm.async_capture_span()
async def parse_base64(data: Union[str, bytes], altchars=b"+/") -> str:
    if isinstance(data, str):
        data = data.encode("UTF-8")
    data = re.sub(rb"[^a-zA-Z0-9%s]+" % altchars, b"", data)  # normalize
    missing_padding = len(data) % 4
    if missing_padding:
        data += b"=" * (4 - missing_padding)

    return base64.urlsafe_b64decode(data).decode("UTF-8")


@elasticapm.async_capture_span()
async def parse_payload(
    element: Union[models.PayloadElementBaseModel, models.PayloadElementPostModel],
    cookies: str,
) -> dict:
    element = element.dict()

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
        element["ue"] = await parse_event(event_context)

    if element.get("rtm") is None:
        element["rtm"] = datetime.utcnow()

    if element.get("stm") is None:
        element["stm"] = datetime.utcnow()

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
    if element.get("duid_amp", ""):
        element["duid"] = element["duid_amp"]
    if element.get("uid_amp", ""):
        element["uid"] = element["uid_amp"]
    if element["e"] == "ue" and "amp_page_ping" in element["ue"]:
        element["e"] = "pp"
        element["extra"]["amp_page_ping"] = element["ue"].pop("amp_page_ping")

    if element["url"] is not None:
        element["url"] = urlparse.unquote(element["url"])

    parsed_url = urlparse.urlparse(element["url"])
    query_string = urlparse.parse_qs(parsed_url.query)

    if query_string.get("sp_amp_linker", []):
        amp_linker = query_string["sp_amp_linker"][0]
        unknown_1, unknown_2, unknown_3, device_id_amp = amp_linker.split("*")
        device_id_amp = await parse_base64(device_id_amp)
        element["device_id_amp"] = device_id_amp

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
            element["screen_extra"][underscore(k)] = v
        _ = element["ue"].pop("screen_view")

    if "screen_extra" in element and "screen_name" in element["screen_extra"]:
        element["url"] = element["screen_extra"].pop("screen_name")

    return element


@elasticapm.async_capture_span()
async def parse_contexts(contexts: dict) -> dict:

    result = {
        "extra": {},
        "user_data": {},
        "device_extra": {},
        "session_extra": {},
        "screen_extra": {},
    }

    for item in contexts["data"]:
        if "schema" not in item:
            print(item)
            continue

        schema = item["schema"]
        data = item["data"]

        if not isinstance(data, dict):
            continue

        if schema.startswith("iglu:com.acme/static_context"):
            for k, v in item["data"].items():
                result["extra"][k] = v
        elif schema.startswith("iglu:org.w3/PerformanceTiming"):
            result["extra"]["performance_timing"] = item["data"]
        elif schema.startswith("iglu:org.ietf/http_client_hints"):
            result["extra"]["client_hints"] = item["data"]
        elif schema.startswith("iglu:com.google.analytics/cookies"):
            result["extra"]["ga_cookies"] = item["data"]
        elif schema.startswith("iglu:com.snowplowanalytics.snowplow/web_page"):
            result["view_id"] = item["data"]["id"]
        elif schema.startswith("iglu:dev.amp.snowplow/amp_id"):
            result["device_id_amp"] = data["ampClientId"]
            result["duid_amp"] = data["domainUserid"]
            result["uid_amp"] = data["userId"]
        elif schema.startswith("iglu:dev.amp.snowplow/amp_web_page"):
            result["view_id"] = item["data"]["ampPageViewId"]
        elif schema.startswith("iglu:dev.snowplow.simple/page_data"):
            result["page_data"] = item["data"]
        elif schema.startswith("iglu:com.snowplowanalytics.snowplow/mobile_context"):
            result["device_brand"] = data.pop("deviceManufacturer")
            result["device_model"] = data.pop("deviceModel")
            device_family = f"{result['device_brand']} {result['device_model']}"
            result["device_family"] = device_family
            result["os_family"] = data.pop("osType")
            result["os_version_string"] = data.pop("osVersion")
            result["os_version"] = result["os_version_string"].split(".")
            result["device_is"] = (1, 0, 1, 0, 0)
            for k, v in data.items():
                result["device_extra"][underscore(k)] = v
        elif schema.startswith("iglu:com.snowplowanalytics.mobile/application/"):
            result["app_extra"] = item["data"]
        elif schema.startswith("iglu:com.snowplowanalytics.snowplow/client_session"):
            result["vid"] = data.pop("sessionIndex")
            result["sid"] = data.pop("sessionId")
            result["duid"] = data.pop("userId")
            for k, v in data.items():
                result["session_extra"][underscore(k)] = v
        elif schema.startswith("iglu:com.snowplowanalytics.mobile/screen/"):
            # data is duplicated in event field is it's view
            result["url"] = data.pop("name")
            result["view_id"] = data.pop("id")
            for key in ("activity", "type"):
                if key in data:
                    result["screen_extra"][key] = data.pop(key)
        elif schema.startswith("iglu:dev.snowplow.simple/screen_data"):
            for k, v in data.items():
                result["screen_extra"][k] = v
        elif schema.startswith("iglu:dev.snowplow.simple/user_data"):
            for k, v in data.items():
                result["user_data"][k] = v
        else:
            print(item)  # add warning

    return result


@elasticapm.async_capture_span()
async def parse_event(event: dict) -> dict:
    event = event["data"]
    event_name = event["schema"].split("/")[-3]
    return {event_name: event["data"]}


@elasticapm.async_capture_span()
async def parse_cookies(cookies_str: str) -> dict:
    result = {}

    if cookies_str is None:
        return result

    cookies_dict = SimpleCookie()
    cookies_dict.load(cookies_str)

    if cookies_dict:
        cookie_name, cookie_value = None, None
        for k, v in cookies_dict.items():
            if k.startswith("_sp_id."):
                cookie_name, cookie_value = k, v.value
                break

        if cookie_value:
            cookie_value = cookie_value.split(".")
            result["device_id"] = cookie_value[0]
            result["created_time"] = cookie_value[1]
            result["visit_count"] = cookie_value[2]
            result["now_time"] = cookie_value[3]
            result["last_visit_time"] = cookie_value[4]
            result["session_id"] = cookie_value[5]

    return result
