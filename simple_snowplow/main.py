from contextlib import asynccontextmanager

import requests
from brotli_asgi import BrotliMiddleware
from clickhouse_connect import get_async_client
from config import settings
from fastapi import FastAPI
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from plugins.logger import init_logging
from plugins.logger import validation_exception_handler
from routers.demo import router as demo_router
from routers.proxy import router as proxy_router
from routers.tracker import router as app_router
from routers.tracker.db.clickhouse import ClickHouseConnector
from starlette.middleware.cors import CORSMiddleware
from starlette.status import HTTP_502_BAD_GATEWAY


@asynccontextmanager
async def lifespan(application):

    ch_conn = settings.clickhouse.connection
    ch_bulk_conn = ch_conn.pop("bulk")
    ch_config = settings.clickhouse.configuration

    application.state.ch_bulk_url = None
    application.state.ch_client = await get_async_client(**ch_conn)
    application.state.connector = ClickHouseConnector(
        application.state.ch_client,
        **ch_config,
    )
    await application.state.connector.create_all()

    if ch_bulk_conn["enabled"]:
        application.state.ch_bulk_url = ch_bulk_conn["url"]
        ch_conn["url"] = ch_bulk_conn["url"]
        ch_config["chbulk_enabled"] = True
        application.state.ch_client = get_async_client(**ch_conn)
        application.state.connector = ClickHouseConnector(
            application.state.ch_client,
            **ch_config,
        )
        application.state.ch_conn_type = "bulk"
    else:
        application.state.ch_conn_type = "direct"

    yield

    application.state.ch_client.close()


app = FastAPI(title="Simple Snowplow", version="0.2.2", lifespan=lifespan)

init_logging()
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

    if request.app.state.ch_bulk_url is None:
        query = await app.state.ch_client.query("SELECT 1")
        ch_status = query.first_row[0] == 1
    else:
        query = requests.get(f"{request.app.state.ch_bulk_url}/status")
        ch_status = query.ok and query.json().get("status") == "ok"

    status = {"clickhouse": ch_status}
    status = jsonable_encoder(status)

    for v in status.values():
        if not v:
            return JSONResponse(content=status, status_code=HTTP_502_BAD_GATEWAY)

    result = JSONResponse(
        content={"status": status, "table": app.state.connector.get_table_name()},
    )

    return result
