"""HTTP-middleware приложения"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

request_logger = logging.getLogger("app.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Логирует каждый HTTP-запрос и ответ в отдельный файл запросов."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Обрабатывает запрос, измеряет длительность и пишет запись в лог."""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            request_logger.exception(
                "request_id=%s method=%s path=%s status=500 duration_ms=%.2f client=%s",
                request_id,
                request.method,
                request.url.path,
                elapsed_ms,
                request.client.host if request.client else "-",
            )
            raise

        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        request_logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.2f client=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request.client.host if request.client else "-",
        )
        return response
