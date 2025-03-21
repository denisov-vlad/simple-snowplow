"""
Main application entry point for Simple Snowplow.
"""
import structlog
from brotli_asgi import BrotliMiddleware
from core.config import settings
from core.healthcheck import probe
from core.lifespan import lifespan
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from middleware.logging import LoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.security import SecurityHeadersMiddleware
from plugins.logger import configure_logger
from plugins.logger import validation_exception_handler
from routers.demo import router as demo_router
from routers.proxy import router as proxy_router
from routers.tracker import router as app_router
from starlette.middleware.cors import CORSMiddleware

# Configure logging
configure_logger(settings.logging.json_format, settings.logging.level)
logger = structlog.stdlib.get_logger()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Simple Snowplow",
        version="0.3.1",
        lifespan=lifespan,
        docs_url=None if settings.security.disable_docs else "/docs",
        redoc_url=None if settings.security.disable_docs else "/redoc",
    )

    # Add middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(BrotliMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Add conditional middleware
    if settings.security.enable_https_redirect:
        app.add_middleware(HTTPSRedirectMiddleware)

    if settings.security.trusted_hosts != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.security.trusted_hosts,
        )

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

    # Add APM middleware if enabled
    if settings.elastic_apm.enabled:
        from elasticapm.contrib.starlette import ElasticAPM
        from plugins.elastic_apm import elastic_apm_client

        app.add_middleware(ElasticAPM, client=elastic_apm_client)

    # Add Prometheus middleware if enabled
    if settings.prometheus.enabled:
        from starlette_exporter import handle_metrics, PrometheusMiddleware

        app.add_middleware(
            PrometheusMiddleware,
            filter_unhandled_paths=False,
            group_paths=True,
        )
        app.add_route(settings.prometheus.metrics_path, handle_metrics)

    return app


app = create_app()
