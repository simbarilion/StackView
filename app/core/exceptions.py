"""Исключения уровня приложения"""

from typing import Any


class AppError(Exception):
    """Базовая ошибка приложения, отображаемая в HTTP-ответ"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "app_error",
        details: Any = None,
    ) -> None:
        """Инициализирует ошибку с сообщением, статусом, кодом и деталями."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


class NotFoundError(AppError):
    """Ошибка 'ресурс не найден' (HTTP 404)"""

    def __init__(self, message: str = "Resource not found", *, details: Any = None) -> None:
        """Создаёт ошибку 404 с опциональными деталями"""
        super().__init__(message, status_code=404, code="not_found", details=details)


class RateLimitError(AppError):
    """Ошибка превышения лимита запросов (HTTP 429)"""

    def __init__(self, message: str = "Too many requests", *, details: Any = None) -> None:
        """Создаёт ошибку 429 с опциональными деталями"""
        super().__init__(message, status_code=429, code="rate_limit_exceeded", details=details)


class ExternalServiceError(AppError):
    """Ошибка недоступности внешнего сервиса (HTTP 502)"""

    def __init__(
        self,
        message: str = "External service unavailable",
        *,
        code: str = "external_service_error",
        details: Any = None,
    ) -> None:
        """Создаёт ошибку 502 с произвольным кодом и деталями"""
        super().__init__(message, status_code=502, code=code, details=details)
