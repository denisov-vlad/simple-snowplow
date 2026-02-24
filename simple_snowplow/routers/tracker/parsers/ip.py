"""
IP address parsing and handling.
"""

from ipaddress import IPv4Address, IPv6Address, ip_address

from elasticapm.contrib.asyncio.traces import async_capture_span

DEFAULT_IPV4 = IPv4Address("0.0.0.0")


@async_capture_span()
async def extract_ip_from_header(
    header_value: str | None,
) -> IPv4Address | IPv6Address | None:
    """
    Parse a header value and return the first valid IP address.

    For comma-separated headers (for example, ``X-Forwarded-For``), the first
    valid value is treated as the original client IP.

    Args:
        header_value: Raw HTTP header value

    Returns:
        First parsed IP address or None
    """
    if not header_value:
        return None

    for part in header_value.split(","):
        candidate = part.strip()
        if not candidate:
            continue
        try:
            return ip_address(candidate)
        except ValueError:
            continue

    return None


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
        ip = await extract_ip_from_header(ip)
        if ip is None:
            return DEFAULT_IPV4

    if isinstance(ip, IPv6Address):
        # Convert IPv6 to IPv4 if it's a mapped address
        if ip.ipv4_mapped:
            return ip.ipv4_mapped
        return DEFAULT_IPV4

    return ip
