"""
IP address parsing and handling.
"""

from ipaddress import IPv4Address, IPv6Address
from typing import Optional, Union

import elasticapm
from pydantic import IPvAnyAddress
from pydantic_core import PydanticCustomError


@elasticapm.async_capture_span()
async def convert_ip(ip: Optional[Union[IPv4Address, IPv6Address, str]]) -> IPv4Address:
    """
    Convert an IP address to IPv4Address format.

    Args:
        ip: The IP address to convert

    Returns:
        The converted IPv4 address or a default address if conversion fails
    """
    none_ip = IPv4Address("0.0.0.0")

    if ip is None:
        return none_ip

    if isinstance(ip, str):
        try:
            ip = IPvAnyAddress(ip)
        except PydanticCustomError:
            return none_ip

    if isinstance(ip, IPv6Address):
        # Convert IPv6 to IPv4 if it's a mapped address
        if ip.ipv4_mapped:
            return ip.ipv4_mapped
        return none_ip

    return ip
