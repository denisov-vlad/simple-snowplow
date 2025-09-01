import base64

import orjson
from elasticapm.contrib.asyncio.traces import async_capture_span


@async_capture_span()
async def parse_base64(data: str | bytes, altchars: bytes = b"+/") -> str:
    """
    Parse base64 encoded data.

    Args:
        data: The base64 encoded data
        altchars: Alternative characters for base64 encoding

    Returns:
        Decoded string
    """

    if isinstance(data, str):
        data_bytes: bytes = data.encode("UTF-8")
    elif isinstance(data, (bytearray, memoryview)):
        data_bytes = bytes(data)
    else:
        data_bytes = data  # already bytes

    missing_padding = len(data_bytes) % 4
    if missing_padding:
        data_bytes = data_bytes + (b"=" * (4 - missing_padding))

    return base64.b64decode(data_bytes, altchars=altchars).decode("UTF-8")


@async_capture_span()
async def find_available(unencoded: str | None, encoded: str | None) -> dict | None:
    result = None

    if unencoded:
        result = unencoded
    elif encoded:
        result = await parse_base64(encoded)

    if result is not None:
        return orjson.loads(result)
