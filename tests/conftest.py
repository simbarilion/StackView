"""Общие фикстуры тестовых модулей"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_rate_limit_service
from app.main import app
from app.repositories.rate_limit import RateLimitRepository
from app.services.rate_limit import RateLimitService


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """TestClient с изолированным rate limit"""
    storage = tmp_path / "rate_limit.json"
    service = RateLimitService(
        repository=RateLimitRepository(storage),
        limit=1000,
        window_seconds=60,
    )
    app.dependency_overrides[get_rate_limit_service] = lambda: service
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_rate_limit_service, None)
