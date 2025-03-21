"""
User agent parsing functionality.
"""

from typing import Any, Dict

import elasticapm
from user_agents import parse


@elasticapm.async_capture_span()
async def parse_agent(string: str) -> Dict[str, Any]:
    """
    Parse a user agent string into structured data.

    Args:
        string: The user agent string to parse

    Returns:
        Dictionary of parsed user agent information
    """
    user_agent = parse(string)

    # Create a structured representation of the user agent
    return {
        "user_agent": string,
        "browser_family": user_agent.browser.family,
        "browser_version": [str(i) for i in user_agent.browser.version],
        "browser_version_string": user_agent.browser.version_string,
        "browser_extra": {},  # Empty placeholder for any additional data
        "os_family": user_agent.os.family,
        "os_version": [str(i) for i in user_agent.os.version],
        "os_version_string": user_agent.os.version_string,
        "lang": "",  # Empty placeholder for language
        "device_brand": user_agent.device.brand or "",
        "device_model": user_agent.device.model or "",
        "device_extra": {},  # Empty placeholder for any additional data
        "device_is": (
            user_agent.is_mobile,
            user_agent.is_tablet,
            user_agent.is_touch_capable,
            user_agent.is_pc,
            user_agent.is_bot,
        ),
    }
