from contextlib import asynccontextmanager

import structlog
from brotli_asgi import BrotliMiddleware
from clickhouse_connect import get_async_client
from config import settings
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from plugins.logger import configure_logger
from plugins.logger import validation_exception_handler
from routers.demo import router as demo_router
from routers.proxy import router as proxy_router
from routers.tracker import router as app_router
from routers.tracker.db.clickhouse import ClickHouseConnector
from starlette.middleware.cors import CORSMiddleware
from starlette.status import HTTP_502_BAD_GATEWAY
from uvicorn.protocols.utils import get_path_with_query_string


@asynccontextmanager
async def lifespan(application):
    application.state.ch_client = await get_async_client(
        **settings.clickhouse.connection,
    )
    application.state.connector = ClickHouseConnector(
        application.state.ch_client,
        **settings.clickhouse.configuration,
    )
    await application.state.connector.create_all()

    yield

    application.state.ch_client.close()


configure_logger(settings.logging.json, settings.logging.level)
logger = structlog.stdlib.get_logger()


app = FastAPI(title="Simple Snowplow", version="0.3.1", lifespan=lifespan)


@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    structlog.contextvars.clear_contextvars()
    response = Response(status_code=500)
    try:
        response: Response = await call_next(request)
    except Exception:
        # TODO: Validate that we don't swallow exceptions (unit test?)
        await structlog.stdlib.get_logger("api.error").exception("Uncaught exception")
        raise
    finally:
        status_code = response.status_code
        url = get_path_with_query_string(request.scope)
        client_host = request.client.host
        client_port = request.client.port
        http_method = request.method
        http_version = request.scope["http_version"]
        # Recreate the Uvicorn access log format, but add all parameters as structured information
        await logger.info(
            f"""{client_host}:{client_port} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
            http={
                "url": str(request.url),
                "status_code": status_code,
                "method": http_method,
                "version": http_version,
            },
            network={"client": {"ip": client_host, "port": client_port}},
        )
        return response


app.add_exception_handler(RequestValidationError, validation_exception_handler)


app.include_router(app_router)
app.include_router(proxy_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


if settings.common.demo:
    app.include_router(demo_router)
    app.mount(
        "/demo",
        StaticFiles(directory="routers/demo/static", html=True),
        name="demo",
    )


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.add_middleware(BrotliMiddleware)
if settings.elastic_apm.enabled:
    from elasticapm.contrib.starlette import ElasticAPM
    from plugins.elastic_apm import elastic_apm_client

    app.add_middleware(ElasticAPM, client=elastic_apm_client)

if settings.prometheus.enabled:
    from starlette_exporter import handle_metrics
    from starlette_exporter import PrometheusMiddleware

    app.add_middleware(
        PrometheusMiddleware,
        filter_unhandled_paths=False,
        group_paths=True,
    )
    app.add_route("/metrics/", handle_metrics)


@app.get("/", include_in_schema=True)
async def probe(request: Request):

    query = await request.app.state.ch_client.query("SELECT 1")
    ch_status = query.first_row[0] == 1

    status = {"clickhouse": ch_status}
    status = jsonable_encoder(status)

    for v in status.values():
        if not v:
            return JSONResponse(content=status, status_code=HTTP_502_BAD_GATEWAY)

    result = JSONResponse(
        content={"status": status, "table": app.state.connector.get_table_name()},
    )

    return result
