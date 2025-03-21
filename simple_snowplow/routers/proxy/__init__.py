import base64

import requests
from core.config import settings
from fastapi.responses import Response
from fastapi.routing import APIRouter
from routers.proxy import models

PROXY_CONFIG = settings.proxy
PROXY_ENDPOINT = settings.common.snowplow.endpoints.proxy_endpoint
HOSTNAME = settings.common.hostname


router = APIRouter(tags=["proxy"], prefix=PROXY_ENDPOINT)


def encode(s: str) -> str:
    return base64.b64encode(s.encode("ascii"), altchars=b"+_").decode("utf-8")


def decode(s: str) -> str:
    return base64.urlsafe_b64decode(s).decode("UTF-8")


@router.post("/hash")
async def proxy_hash(data: models.HashModel):
    return_encoded = False

    domain = data.url.host
    if domain in PROXY_CONFIG.domains:
        domain = encode(domain)
        return_encoded = True

    full_path = data.url.path[1:]
    if data.url.query is not None:
        full_path += f"?{data.url.query}"

    if data.url.path[1:] in PROXY_CONFIG.paths:
        full_path = encode(full_path)
        return_encoded = True

    if not return_encoded:
        return data.url

    result = (
        f"{HOSTNAME}{PROXY_ENDPOINT}/route/{data.url.scheme}/"
        f"{encode(data.url.host)}/{full_path}"
    )

    return result


@router.get("/route/{schema}/{host}/{path}")
async def proxy(schema: str, host: str, path: str = ""):
    url = f"{schema}://{decode(host)}/{decode(path)}"

    r = requests.get(url)
    content = r.content

    return Response(
        content=content,
        status_code=r.status_code,
        media_type=r.headers["Content-Type"],
    )
