"""Тесты API формы обратной связи"""

from fastapi.testclient import TestClient


def test_contact_success(client: TestClient, raw_contact_payload: dict[str, str]) -> None:
    """Успешный POST /api/contact возвращает 201 и санитизированные поля"""
    response = client.post("/api/contact", json=raw_contact_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "accepted"
    assert body["name"] == "Иван Иванов"
    assert body["email"] == "ivan@example.com"
    assert body["phone"] == "+79991234567"
    assert body["comment"] == "Здравствуйте! Хочу обсудить проект."
    assert "message" in body
    assert "email_sent" in body


def test_contact_validation_missing_fields(client: TestClient) -> None:
    """Отсутствие обязательных полей даёт 422 validation_error"""
    response = client.post("/api/contact", json={"name": "Иван"})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"


def test_contact_invalid_email(client: TestClient, valid_payload: dict[str, str]) -> None:
    """Некорректный email даёт 422"""
    payload = {**valid_payload, "email": "not-an-email"}
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422


def test_contact_invalid_phone(client: TestClient, valid_payload: dict[str, str]) -> None:
    """Телефон без достаточного числа цифр даёт 422"""
    payload = {**valid_payload, "phone": "123"}
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"


def test_contact_phone_too_many_digits(client: TestClient, valid_payload: dict[str, str]) -> None:
    """Слишком длинный телефон даёт сериализуемый 422 с полем phone"""
    payload = {**valid_payload, "phone": "+799912345678901234"}
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["details"], list)
    locs = [item.get("loc") for item in body["details"]]
    assert any("phone" in loc for loc in locs if isinstance(loc, list))


def test_contact_strips_html_from_comment(client: TestClient, valid_payload: dict[str, str]) -> None:
    """HTML-теги в комментарии удаляются при санитизации"""
    payload = {**valid_payload, "comment": "<script>alert(1)</script>Привет"}
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 201
    assert "<script>" not in response.json()["comment"]
    assert "Привет" in response.json()["comment"]
