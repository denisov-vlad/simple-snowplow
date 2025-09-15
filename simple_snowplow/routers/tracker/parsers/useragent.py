"""
User agent parsing functionality.
"""

from typing import Any

from crawlerdetect import CrawlerDetect
from elasticapm.contrib.asyncio.traces import async_capture_span
from ua_parser import parse

crawler_detect = CrawlerDetect()


async def remove_none_values(data: list[str | None]) -> list[str]:
    return [item for item in data if item is not None]


@async_capture_span()
async def parse_agent(string: str | None) -> dict[str, Any]:
    """
    Parse a user agent string into structured data.

    Args:
        string: The user agent string to parse

    Returns:
        Dictionary of parsed user agent information
    """

    data = {
        "user_agent": "",
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
        "device_is_mobile": False,
        "device_is_tablet": False,
        "device_is_touch_capable": False,
        "device_is_pc": False,
        "device_is_bot": False,
    }

    if string is None:
        return data

    ua = parse(string)
    data["user_agent"] = string
    data["device_is_bot"] = crawler_detect.isCrawler(string)

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
