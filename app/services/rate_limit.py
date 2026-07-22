"""Сервис ограничения частоты запросов."""

from app.core.exceptions import RateLimitError
from app.repositories.rate_limit import RateLimitRepository


class RateLimitService:
    """Проверяет лимит запросов через файловый репозиторий"""

    def __init__(
        self,
        repository: RateLimitRepository,
        *,
        limit: int,
        window_seconds: int,
    ) -> None:
        """Сохраняет репозиторий и параметры fixed window"""
        self._repository = repository
        self._limit = limit
        self._window_seconds = window_seconds

    def ensure_allowed(self, client_ip: str) -> None:
        """Разрешает запрос или поднимает RateLimitError при превышении лимита"""
        allowed = self._repository.register_hit(
            client_ip,
            limit=self._limit,
            window_seconds=self._window_seconds,
        )
        if allowed:
            return

        retry_after = self._repository.seconds_until_reset(
            client_ip,
            window_seconds=self._window_seconds,
        )
        raise RateLimitError(
            "Too many requests. Please try again later.",
            details={
                "limit": self._limit,
                "window_seconds": self._window_seconds,
                "retry_after": retry_after,
                "client_ip": client_ip,
            },
        )
