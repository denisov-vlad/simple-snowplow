"""
User agent parsing functionality.
"""

from typing import Any

import elasticapm
from crawlerdetect import CrawlerDetect
from ua_parser import parse

crawler_detect = CrawlerDetect()


async def remove_none_values(data: list[str | None]) -> list[str]:
    return [item for item in data if item is not None]


@elasticapm.async_capture_span()
async def parse_agent(string: str) -> dict[str, Any]:
    """
    Parse a user agent string into structured data.

    Args:
        string: The user agent string to parse

    Returns:
        Dictionary of parsed user agent information
    """
    ua = parse(string)
    is_bot = int(crawler_detect.isCrawler(string))

    data = {
        "user_agent": string,
        "browser_family": "",
        "browser_version": [],
        "browser_version_string": "",
        "browser_extra": {},
        "os_family": "",
        "os_version": [],
        "os_version_string": "",
        "lang": "",
        "device_brand": "",
        "device_model": "",
        "device_extra": {},
        "device_is_mobile": 0,
        "device_is_tablet": 0,
        "device_is_touch_capable": 0,
        "device_is_pc": 0,
        "device_is_bot": is_bot,
    }

    if ua is None:
        return data

    browser = ua.user_agent
    if browser is not None:
        data["browser_family"] = browser.family or ""
        data["browser_version"] = await remove_none_values([
            browser.major,
            browser.minor,
            browser.patch,
            browser.patch_minor,
        ])
        data["browser_version_string"] = ".".join(data["browser_version"])

    os = ua.os
    if os is not None:
        data["os_family"] = os.family or ""
        data["os_version"] = await remove_none_values([
            os.major,
            os.minor,
            os.patch,
            os.patch_minor,
        ])
        data["os_version_string"] = ".".join(data["os_version"])

    device = ua.device
    if device is not None:
        data["device_brand"] = device.brand or ""
        data["device_model"] = device.model or ""
        if device.family:
            data["device_extra"]["family"] = device.family

    return data
