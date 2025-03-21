from datetime import datetime

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.protocols.utils import get_path_with_query_string


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        structlog.contextvars.clear_contextvars()
        response = Response(status_code=500)
        start_time = datetime.now()
        logger = structlog.stdlib.get_logger()

        try:
            response: Response = await call_next(request)
        except Exception as e:
            # Log exception details for better debugging
            await structlog.stdlib.get_logger("api.error").exception(
                "Uncaught exception",
                exc_info=e,
                url=str(request.url),
                method=request.method,
                client_host=request.client.host if request.client else "unknown",
            )
            raise
        finally:
            status_code = response.status_code
            url = get_path_with_query_string(request.scope)
            client_host = request.client.host if request.client else "unknown"
            client_port = request.client.port if request.client else 0
            http_method = request.method
            http_version = request.scope["http_version"]
            process_time = (datetime.now() - start_time).total_seconds()

            # Recreate the Uvicorn access log format, but add all parameters
            # as structured information
            await logger.info(
                f"""{client_host}:{client_port} - "{http_method} {url} """
                f"""HTTP/{http_version}" {status_code} - {process_time:.3f}s""",
                http={
                    "url": str(request.url),
                    "status_code": status_code,
                    "method": http_method,
                    "version": http_version,
                    "process_time_seconds": process_time,
                },
                network={"client": {"ip": client_host, "port": client_port}},
            )
            return response
