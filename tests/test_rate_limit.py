"""Тесты file-backed rate limiting для POST /api/contact"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_ai_service, get_contact_repository, get_rate_limit_service
from app.core.config import get_settings
from app.main import app
from app.repositories.rate_limit import RateLimitRepository
from app.schemas.ai import AIEnrichment
from app.services.rate_limit import RateLimitService


@pytest.fixture
def rate_limit_client(tmp_path: Path):
    """Клиент с лимитом 2 запроса / 60 сек и изолированным JSON-файлом"""
    storage = tmp_path / "rate_limit.json"
    service = RateLimitService(
        repository=RateLimitRepository(storage),
        limit=2,
        window_seconds=60,
    )
    ai = AsyncMock()
    ai.enrich = AsyncMock(return_value=AIEnrichment(ai_available=False))
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=MagicMock(id=1))
    app.dependency_overrides[get_rate_limit_service] = lambda: service
    app.dependency_overrides[get_ai_service] = lambda: ai
    app.dependency_overrides[get_contact_repository] = lambda: repo
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_rate_limit_service, None)
    app.dependency_overrides.pop(get_ai_service, None)
    app.dependency_overrides.pop(get_contact_repository, None)


def test_rate_limit_allows_within_window(
    rate_limit_client: TestClient,
    valid_payload: dict[str, str],
) -> None:
    """Первые n запросов в окне проходят успешно"""
    for _ in range(2):
        response = rate_limit_client.post("/api/contact", json=valid_payload)
        assert response.status_code == 201


def test_rate_limit_blocks_excess_requests(
    rate_limit_client: TestClient,
    valid_payload: dict[str, str],
) -> None:
    """Запрос сверх лимита возвращает 429 rate_limit_exceeded"""
    assert rate_limit_client.post("/api/contact", json=valid_payload).status_code == 201
    assert rate_limit_client.post("/api/contact", json=valid_payload).status_code == 201

    response = rate_limit_client.post("/api/contact", json=valid_payload)
    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "rate_limit_exceeded"
    assert "retry_after" in (body.get("details") or {})


def test_rate_limit_repository_resets_window(tmp_path: Path) -> None:
    """После истечения окна счётчик сбрасывается"""
    repo = RateLimitRepository(tmp_path / "rate_limit.json")
    assert repo.register_hit("1.2.3.4", limit=1, window_seconds=10, now=1000.0) is True
    assert repo.register_hit("1.2.3.4", limit=1, window_seconds=10, now=1001.0) is False
    assert repo.register_hit("1.2.3.4", limit=1, window_seconds=10, now=1010.0) is True


def test_settings_expose_rate_limit_values() -> None:
    """Лимит и окно читаются из настроек окружения"""
    settings = get_settings()
    assert settings.rate_limit_requests >= 1
    assert settings.rate_limit_window_seconds >= 1
