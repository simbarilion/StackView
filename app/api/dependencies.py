"""Общие зависимости FastAPI"""

from pathlib import Path

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.dependencies import get_session
from app.repositories.contact import ContactRepository
from app.repositories.rate_limit import RateLimitRepository
from app.services.ai import AIService
from app.services.contact import ContactService
from app.services.email import EmailService
from app.services.rate_limit import RateLimitService


def settings_dep() -> Settings:
    """Возвращает настройки приложения для внедрения через Depends"""
    return get_settings()


def get_email_service(settings: Settings = Depends(settings_dep)) -> EmailService:
    """Возвращает сервис отправки email"""
    return EmailService(settings)


def get_ai_service(settings: Settings = Depends(settings_dep)) -> AIService:
    """Возвращает сервис AI-анализа обращений"""
    return AIService(settings)


def get_contact_repository(
    session: AsyncSession = Depends(get_session),
) -> ContactRepository:
    """Возвращает репозиторий обращений"""
    return ContactRepository(session)


def get_contact_service(
    email_service: EmailService = Depends(get_email_service),
    ai_service: AIService = Depends(get_ai_service),
    contact_repository: ContactRepository = Depends(get_contact_repository),
) -> ContactService:
    """Возвращает оркестратор обращений ContactService"""
    return ContactService(email_service, ai_service, contact_repository)


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
