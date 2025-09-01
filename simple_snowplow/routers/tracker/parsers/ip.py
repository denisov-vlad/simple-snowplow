"""
IP address parsing and handling.
"""

from ipaddress import IPv4Address, IPv6Address, ip_address

from elasticapm.contrib.asyncio.traces import async_capture_span

DEFAULT_IPV4 = IPv4Address("0.0.0.0")


@async_capture_span()
async def convert_ip(ip: IPv4Address | IPv6Address | str | None) -> IPv4Address:
    """
    Convert an IP address to IPv4Address format.

    Args:
        ip: The IP address to convert

    Returns:
        The converted IPv4 address or a default address if conversion fails
    """

    if ip is None:
        return DEFAULT_IPV4
    elif isinstance(ip, IPv4Address):
        return ip
    elif isinstance(ip, str):
        try:
            ip = ip_address(ip)
        except ValueError:
            return DEFAULT_IPV4

    if isinstance(ip, IPv6Address):
        # Convert IPv6 to IPv4 if it's a mapped address
        if ip.ipv4_mapped:
            return ip.ipv4_mapped
        return DEFAULT_IPV4

    return ip
