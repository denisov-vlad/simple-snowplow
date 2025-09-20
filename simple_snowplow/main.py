"""
Main application entry point for Simple Snowplow.
"""

from asgi_correlation_id.middleware import CorrelationIdMiddleware
from brotli_asgi import BrotliMiddleware
from core.config import settings
from core.healthcheck import probe
from core.lifespan import lifespan
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware import Middleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_structlog.middleware import (
    AccessLogMiddleware,
    CurrentScopeSetMiddleware,
    StructlogMiddleware,
)
from middleware.rate_limit import RateLimitMiddleware
from middleware.security import SecurityHeadersMiddleware
from plugins.logger import init_logging, validation_exception_handler
from routers.demo import router as demo_router
from routers.proxy import router as proxy_router
from routers.tracker import router as app_router
from starlette.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Configure logging using fastapi-structlog
    init_logging(settings.logging.json_format, settings.logging.level)

    app = FastAPI(
        title="Simple Snowplow",
        version="0.4.0",
        lifespan=lifespan,
        docs_url=None if settings.security.disable_docs else "/docs",
        redoc_url=None if settings.security.disable_docs else "/redoc",
        middlewares=[
            Middleware(
                CORSMiddleware,
                allow_origin_regex=".*",
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["*"],
            ),
            Middleware(CurrentScopeSetMiddleware),
            Middleware(CorrelationIdMiddleware),
            Middleware(StructlogMiddleware),
            Middleware(AccessLogMiddleware),
            Middleware(SecurityHeadersMiddleware),
            Middleware(RateLimitMiddleware),
            Middleware(BrotliMiddleware),
        ],
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
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator().instrument(app).expose(
            app,
            include_in_schema=False,
            should_gzip=True,
        )

    if settings.sentry.enabled:
        from fastapi_structlog.sentry import SentrySettings, setup_sentry

        sentry_settings = SentrySettings.model_validate(
            {
                "dsn": settings.sentry.dsn,
                "environment": settings.sentry.environment,
                "traces_sample_rate": settings.sentry.traces_sample_rate,
            },
        )
        setup_sentry(
            sentry_settings,
            app_slug=settings.common.service_name,
            version=app.version,
        )

    return app


app = create_app()
