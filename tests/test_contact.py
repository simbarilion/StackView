"""Тесты API формы обратной связи (этап 1, без AI/email)"""

from fastapi.testclient import TestClient

VALID_PAYLOAD = {
    "name": "  Иван Иванов  ",
    "phone": "+7 (999) 123-45-67",
    "email": "ivan@example.com",
    "comment": "  Здравствуйте! Хочу обсудить проект.  ",
}


def test_contact_success(client: TestClient) -> None:
    """Успешный POST /api/contact возвращает 201 и санитизированные поля"""
    response = client.post("/api/contact", json=VALID_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "accepted"
    assert body["name"] == "Иван Иванов"
    assert body["email"] == "ivan@example.com"
    assert body["phone"] == "+79991234567"
    assert body["comment"] == "Здравствуйте! Хочу обсудить проект."
    assert "message" in body


def test_contact_validation_missing_fields(client: TestClient) -> None:
    """Отсутствие обязательных полей даёт 422 validation_error"""
    response = client.post("/api/contact", json={"name": "Иван"})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"


def test_contact_invalid_email(client: TestClient) -> None:
    """Некорректный email даёт 422"""
    payload = {**VALID_PAYLOAD, "email": "not-an-email"}
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422


def test_contact_invalid_phone(client: TestClient) -> None:
    """Телефон без достаточного числа цифр даёт 422"""
    payload = {**VALID_PAYLOAD, "phone": "123"}
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422


def test_contact_strips_html_from_comment(client: TestClient) -> None:
    """HTML-теги в комментарии удаляются при санитизации"""
    payload = {**VALID_PAYLOAD, "comment": "<script>alert(1)</script>Привет"}
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 201
    assert "<script>" not in response.json()["comment"]
    assert "Привет" in response.json()["comment"]
