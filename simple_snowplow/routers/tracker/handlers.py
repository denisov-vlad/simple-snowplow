from ipaddress import IPv4Address
from ipaddress import IPv6Address

import elasticapm
from pydantic import IPvAnyAddress
from pydantic_core import PydanticCustomError
from routers.tracker import snowplow
from routers.tracker.useragent import parse_agent


async def convert_ip(ip: IPv4Address | IPv6Address | None) -> IPv4Address:

    none_ip = IPv4Address("0.0.0.0")

    if ip is None:
        return none_ip

    if isinstance(ip, str):
        try:
            ip = IPvAnyAddress(ip)
        except PydanticCustomError:
            return none_ip

    if isinstance(ip, IPv6Address):
        return ip.ipv4_mapped

    return ip


@elasticapm.async_capture_span()
async def process_data(body, user_agent, user_ip, cookies):
    base = {"user_ip": await convert_ip(user_ip)}
    if user_agent:
        ua_data = await parse_agent(user_agent)
        base = dict(base, **ua_data)

    try:
        data = body.data
    except AttributeError:
        data = [body]

    result = []

    for i in data:
        payload_data = await snowplow.parse_payload(i, cookies)
        item_data = dict(base, **payload_data)

        result.append(item_data)

    return result
