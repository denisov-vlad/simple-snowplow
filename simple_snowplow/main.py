import structlog
from brotli_asgi import BrotliMiddleware
from config import settings
from core import lifespan
from core import probe
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from middleware import ENABLE_HTTPS_REDIRECT
from middleware import logging_middleware
from middleware import RateLimitMiddleware
from middleware import SecurityHeadersMiddleware
from middleware import TRUSTED_HOSTS
from plugins.logger import configure_logger
from plugins.logger import validation_exception_handler
from routers.demo import router as demo_router
from routers.proxy import router as proxy_router
from routers.tracker import router as app_router
from starlette.middleware.cors import CORSMiddleware

configure_logger(settings.logging.json, settings.logging.level)
logger = structlog.stdlib.get_logger()

app = FastAPI(
    title="Simple Snowplow",
    version="0.3.1",
    lifespan=lifespan,
    docs_url=None if settings.get("security.disable_docs", False) else "/docs",
    redoc_url=None if settings.get("security.disable_docs", False) else "/redoc",
)


# Add the logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    return await logging_middleware(request, call_next)


# Add exception handler
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Include routers
app.include_router(app_router)
app.include_router(proxy_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add demo router if enabled
if settings.common.demo:
    app.include_router(demo_router)
    app.mount(
        "/demo",
        StaticFiles(directory="routers/demo/static", html=True),
        name="demo",
    )

# Add healthcheck endpoint
app.add_api_route("/", probe, methods=["GET"], include_in_schema=True)

# Add security middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

if ENABLE_HTTPS_REDIRECT:
    app.add_middleware(HTTPSRedirectMiddleware)

if TRUSTED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add compression middleware
app.add_middleware(BrotliMiddleware)

# Add APM middleware if enabled
if settings.elastic_apm.enabled:
    from elasticapm.contrib.starlette import ElasticAPM
    from plugins.elastic_apm import elastic_apm_client

    app.add_middleware(ElasticAPM, client=elastic_apm_client)

# Add Prometheus middleware if enabled
if settings.prometheus.enabled:
    from starlette_exporter import handle_metrics
    from starlette_exporter import PrometheusMiddleware

    app.add_middleware(
        PrometheusMiddleware,
        filter_unhandled_paths=False,
        group_paths=True,
    )
    app.add_route("/metrics/", handle_metrics)
