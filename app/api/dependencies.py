"""Общие зависимости FastAPI"""

from pathlib import Path

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.repositories.rate_limit import RateLimitRepository
from app.services.contact import ContactService
from app.services.rate_limit import RateLimitService


def settings_dep() -> Settings:
    """Возвращает настройки приложения для внедрения через Depends"""
    return get_settings()


def get_contact_service() -> ContactService:
    """Возвращает оркестратор обращений ContactService"""
    return ContactService()


def get_rate_limit_service(settings: Settings = Depends(settings_dep)) -> RateLimitService:
    """Создаёт сервис rate limit с JSON-хранилищем в data_dir"""
    storage = Path(settings.data_dir) / "rate_limit.json"
    return RateLimitService(
        repository=RateLimitRepository(storage),
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )


def enforce_contact_rate_limit(
    request: Request,
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
) -> None:
    """Проверяет лимит для IP клиента до бизнес-логики contact"""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_service.ensure_allowed(client_ip)
