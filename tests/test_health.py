"""Тесты проверки состояния сервиса"""

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    """Проверяет успешный ответ GET /api/health"""
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body
