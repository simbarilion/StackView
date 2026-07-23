"""Тесты лендинга"""

from fastapi.testclient import TestClient


def test_landing_page_renders(client: TestClient) -> None:
    """GET / отдаёт HTML лендинга с формой"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="contact-form"' in response.text
    assert "/static/css/landing.css" in response.text


def test_landing_static_css(client: TestClient) -> None:
    """Статический CSS лендинга доступен"""
    response = client.get("/static/css/landing.css")
    assert response.status_code == 200
    assert "--accent" in response.text
