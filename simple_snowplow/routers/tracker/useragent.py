import elasticapm
from user_agents import parse


@elasticapm.async_capture_span()
async def parse_agent(string: str) -> dict:
    user_agent = parse(string)
    return {
        "user_agent": string,
        "browser_family": user_agent.browser.family,
        "browser_version": [str(i) for i in user_agent.browser.version],
        "browser_version_string": user_agent.browser.version_string,
        "os_family": user_agent.os.family,
        "os_version": [str(i) for i in user_agent.os.version],
        "os_version_string": user_agent.os.version_string,
        "device_brand": user_agent.device.brand,
        "device_model": user_agent.device.model,
        "device_is": (
            int(user_agent.is_mobile),
            int(user_agent.is_tablet),
            int(user_agent.is_touch_capable),
            int(user_agent.is_pc),
            int(user_agent.is_bot),
        ),
    }
