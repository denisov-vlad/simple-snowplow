"""Logging integration using fastapi-structlog.

This replaces the previous custom Structlog configuration with the
`fastapi-structlog` helper utilities so we can rely on its battle-tested
middleware, processors and optional destinations (console / JSON / file / syslog / DB).
"""

import structlog
from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi_structlog import LogSettings, setup_logger
from fastapi_structlog.settings import DBSettings, LogType, SysLogSettings


def init_logging(enable_json_logs: bool, log_level: str) -> None:
    """Initialize logging via fastapi-structlog.

    Args:
        enable_json_logs: Whether logs should be emitted in JSON format.
        log_level: Base log level (string like INFO, DEBUG).
    """

    settings = LogSettings(
        logger="simple_snowplow",
        log_level=log_level.upper(),
        json_logs=enable_json_logs,
        traceback_as_str=True,
        # Only console output for now. JSON vs pretty decided by json_logs flag.
        types=[LogType.CONSOLE],
        syslog=SysLogSettings(),
        db=DBSettings(),
    )

    # Configure structlog / stdlib logging.
    setup_logger(settings)

    # Bind default contextual information (can be enriched in middlewares/routes)
    structlog.contextvars.bind_contextvars(service="simple-snowplow")


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Unified validation error handler using the configured structlog logger."""
    error_data = {"detail": exc.errors(), "body": exc.body}
    logger = structlog.get_logger()
    logger.error("Validation error", **error_data)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_data),
    )
