"""Тесты эндпоинта метрик обращений"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.schemas.metrics import MetricsResponse


def test_get_metrics(client: TestClient, mock_contact_repository: AsyncMock) -> None:
    """GET /api/metrics возвращает агрегаты из репозитория"""
    mock_contact_repository.get_metrics = AsyncMock(
        return_value=MetricsResponse(
            total_submissions=10,
            email_sent=8,
            ai_available=6,
            by_category={"collaboration": 4, "question": 6},
            by_sentiment={"positive": 5, "neutral": 5},
        )
    )

    response = client.get("/api/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["total_submissions"] == 10
    assert body["email_sent"] == 8
    assert body["ai_available"] == 6
    assert body["by_category"]["collaboration"] == 4
    assert body["by_sentiment"]["positive"] == 5
