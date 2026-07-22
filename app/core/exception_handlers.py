import logging
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str | None:
    """Возвращает идентификатор запроса из заголовков"""
    request_id = cast(str | None, request.headers.get("X-Request-ID"))

    if request_id is None:
        request_id = cast(str | None, request.headers.get("x-request-id"))

    return request_id


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Обрабатывает доменные ошибки приложения"""
    payload = ErrorResponse(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Обрабатывает ошибки валидации входных данных (HTTP 422)"""
    payload = ErrorResponse(
        code="validation_error",
        message="Request validation failed",
        details=exc.errors(),
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=422, content=payload.model_dump())


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Обрабатывает стандартные HTTP-исключения Starlette/FastAPI"""
    detail: Any = exc.detail
    payload = ErrorResponse(
        code="http_error",
        message=detail if isinstance(detail, str) else "HTTP error",
        details=None if isinstance(detail, str) else detail,
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Обрабатывает неперехваченные исключения (HTTP 500)"""
    settings = get_settings()
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    payload = ErrorResponse(
        code="internal_error",
        message=str(exc) if settings.app_debug else "Internal server error",
        details=None,
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=500, content=payload.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики исключений"""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
