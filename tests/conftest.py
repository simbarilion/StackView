"""Общие фикстуры и тестовые данные"""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_ai_service,
    get_contact_repository,
    get_email_service,
    get_rate_limit_service,
)
from app.core.config import Settings, clear_settings_cache, get_settings
from app.core.exceptions import ExternalServiceError
from app.main import app
from app.repositories.rate_limit import RateLimitRepository
from app.schemas.ai import AIAnalysisResult, AIEnrichment
from app.schemas.contact import ContactRequest
from app.services.ai import AIService
from app.services.email import EmailService
from app.services.rate_limit import RateLimitService

VALID_PAYLOAD: dict[str, str] = {
    "name": "Иван Иванов",
    "phone": "+79991234567",
    "email": "ivan@example.com",
    "comment": "Хочу обсудить проект",
}

RAW_CONTACT_PAYLOAD: dict[str, str] = {
    "name": "  Иван Иванов  ",
    "phone": "+7 (999) 123-45-67",
    "email": "ivan@example.com",
    "comment": "  Здравствуйте! Хочу обсудить проект.  ",
}


@pytest.fixture
def valid_payload() -> dict[str, str]:
    """Копия валидного payload формы обратной связи"""
    return dict(VALID_PAYLOAD)


@pytest.fixture
def raw_contact_payload() -> dict[str, str]:
    """Payload с лишними пробелами для проверки санитизации"""
    return dict(RAW_CONTACT_PAYLOAD)


@pytest.fixture
def contact_request(valid_payload: dict[str, str]) -> ContactRequest:
    """Валидный ContactRequest для юнит-тестов"""
    return ContactRequest(**valid_payload)


@pytest.fixture
def development_email_settings() -> Settings:
    """Настройки development без SMTP (письма пропускаются)"""
    clear_settings_cache()
    return get_settings().model_copy(
        update={
            "app_env": "development",
            "smtp_host": None,
            "mail_from": None,
            "mail_to_owner": None,
        }
    )


@pytest.fixture
def production_email_settings() -> Settings:
    """Настройки production без SMTP (ожидается 502)"""
    clear_settings_cache()
    return get_settings().model_copy(
        update={
            "app_env": "production",
            "smtp_host": None,
            "mail_from": None,
            "mail_to_owner": None,
        }
    )


@pytest.fixture
def configured_email_settings() -> Settings:
    """Настройки с заполненным SMTP для успешной/неуспешной отправки"""
    clear_settings_cache()
    return get_settings().model_copy(
        update={
            "app_env": "development",
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_use_tls": True,
            "smtp_username": "user",
            "smtp_password": "pass",
            "mail_from": "noreply@example.com",
            "mail_to_owner": "owner@example.com",
        }
    )


@pytest.fixture
def configured_email_service(configured_email_settings: Settings) -> EmailService:
    """EmailService с заполненными SMTP-настройками"""
    return EmailService(configured_email_settings)


@pytest.fixture
def configured_ai_settings() -> Settings:
    """Настройки с включённым AI и тестовым API-ключом"""
    clear_settings_cache()
    return get_settings().model_copy(
        update={
            "ai_enabled": True,
            "openai_api_key": "sk-test-key",
            "openai_model": "gpt-4o-mini",
            "ai_timeout_seconds": 5.0,
        }
    )


@pytest.fixture
def disabled_ai_settings() -> Settings:
    """Настройки с отключённым AI / без ключа"""
    clear_settings_cache()
    return get_settings().model_copy(
        update={
            "ai_enabled": True,
            "openai_api_key": None,
        }
    )


@pytest.fixture
def configured_ai_service(configured_ai_settings: Settings) -> AIService:
    """AIService с ключом"""
    return AIService(configured_ai_settings)


@pytest.fixture
def mock_email_ok() -> AsyncMock:
    """Подмена email-сервиса: отправка всегда успешна"""
    service = AsyncMock()
    service.send_contact_emails.return_value = True
    app.dependency_overrides[get_email_service] = lambda: service
    return service


@pytest.fixture
def mock_email_fail() -> AsyncMock:
    """Подмена email-сервиса: отправка всегда падает с 502"""
    service = AsyncMock()
    service.send_contact_emails.side_effect = ExternalServiceError(
        "Failed to send contact emails",
        code="email_send_failed",
    )
    app.dependency_overrides[get_email_service] = lambda: service
    return service


@pytest.fixture
def mock_ai_ok() -> AsyncMock:
    """Подмена AI: enrich всегда успешен"""
    service = AsyncMock()
    service.enrich.return_value = AIEnrichment(
        ai_available=True,
        ai_analysis=AIAnalysisResult(
            category="collaboration",
            category_label="Сотрудничество",
            sentiment="positive",
            sentiment_score=0.8,
        ),
        suggested_reply="Здравствуйте! Спасибо за обращение.",
    )
    app.dependency_overrides[get_ai_service] = lambda: service
    return service


@pytest.fixture
def mock_ai_unavailable() -> AsyncMock:
    """Подмена AI: enrich без доступного AI"""
    service = AsyncMock()
    service.enrich.return_value = AIEnrichment(ai_available=False)
    app.dependency_overrides[get_ai_service] = lambda: service
    return service


@pytest.fixture
def mock_contact_repository() -> AsyncMock:
    """Подмена репозитория обращений: create всегда успешен"""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=MagicMock(id=1))
    app.dependency_overrides[get_contact_repository] = lambda: repo
    return repo


@pytest.fixture
def client(tmp_path: Path, mock_contact_repository: AsyncMock) -> Iterator[TestClient]:
    """TestClient с изолированным rate limit, моком AI и репозитория"""
    storage = tmp_path / "rate_limit.json"
    rate_limit = RateLimitService(
        repository=RateLimitRepository(storage),
        limit=1000,
        window_seconds=60,
    )
    ai = AsyncMock()
    ai.enrich = AsyncMock(return_value=AIEnrichment(ai_available=False))

    app.dependency_overrides[get_rate_limit_service] = lambda: rate_limit
    app.dependency_overrides[get_ai_service] = lambda: ai
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_rate_limit_service, None)
    app.dependency_overrides.pop(get_email_service, None)
    app.dependency_overrides.pop(get_ai_service, None)
    app.dependency_overrides.pop(get_contact_repository, None)
