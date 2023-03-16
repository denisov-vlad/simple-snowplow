from contextlib import asynccontextmanager

from aiochclient import ChClient
from aiohttp import ClientSession
from brotli_asgi import BrotliMiddleware
from config import settings
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from plugins.logger import init_logging
from routers.demo import router as demo_router
from routers.tracker import router as app_router
from routers.tracker.db import ClickHouseConnector
from routers.tracker.db.clickhouse.lib import ChClientBulk
from starlette.middleware.cors import CORSMiddleware
from starlette.status import HTTP_502_BAD_GATEWAY


@asynccontextmanager
async def lifespan(application):
    application.state.ch_session = ClientSession()

    ch_conn = settings.clickhouse.connection
    ch_bulk_conn = ch_conn.pop("bulk")
    ch_config = settings.clickhouse.configuration

    application.state.ch_client = ChClient(application.state.ch_session, **ch_conn)
    application.state.connector = ClickHouseConnector(
        application.state.ch_client, **ch_config
    )
    await application.state.connector.create_all()

    if ch_bulk_conn["enabled"]:
        await application.state.ch_client.close()
        await application.state.ch_session.close()

        application.state.ch_session = ClientSession()

        ch_conn["url"] = ch_bulk_conn["url"]
        ch_config["chbulk_enabled"] = True
        application.state.ch_client = ChClientBulk(
            application.state.ch_session, **ch_conn
        )
        application.state.connector = ClickHouseConnector(
            application.state.ch_client, **ch_config
        )
        application.state.ch_conn_type = "bulk"
    else:
        application.state.ch_conn_type = "direct"

    yield

    await application.state.ch_client.close()
    await application.state.ch_session.close()


app = FastAPI(title="Simple Snowplow", version="0.1.1", lifespan=lifespan)

init_logging()

app.include_router(app_router)
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
async def probe():
    status = {"clickhouse": await app.state.ch_client.is_alive()}
    status = jsonable_encoder(status)

    for v in status.values():
        if not v:
            return JSONResponse(content=status, status_code=HTTP_502_BAD_GATEWAY)

    result = JSONResponse(
        content={"status": status, "table": app.state.connector.get_table_name()},
    )

    return result
