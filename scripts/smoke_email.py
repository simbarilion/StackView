"""Ручная проверка email-слоя без реальной SMTP-отправки"""

from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.config import Settings, clear_settings_cache, get_settings
from app.core.exceptions import ExternalServiceError
from app.main import app
from app.schemas.contact import ContactRequest
from app.services.email import EmailService


def _settings(**overrides: object) -> Settings:
    clear_settings_cache()
    return cast(Settings, get_settings().model_copy(update=overrides))


async def check_skip_when_unconfigured() -> None:
    """В development без SMTP отправка пропускается"""
    settings = _settings(
        app_env="development",
        smtp_host=None,
        mail_from=None,
        mail_to_owner=None,
    )
    service = EmailService(settings)
    payload = ContactRequest(
        name="Иван Иванов",
        phone="+79991234567",
        email="ivan@example.com",
        comment="Тест",
    )
    sent = await service.send_contact_emails(payload)
    assert sent is False
    print("OK: unconfigured SMTP skipped in development")


async def check_send_both_via_mock() -> None:
    """При настроенном SMTP оба письма уходят в одной сессии"""
    settings = _settings(
        app_env="development",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_use_tls=True,
        smtp_username="user",
        smtp_password="pass",
        mail_from="noreply@example.com",
        mail_to_owner="owner@example.com",
    )
    service = EmailService(settings)
    payload = ContactRequest(
        name="Иван Иванов",
        phone="+79991234567",
        email="ivan@example.com",
        comment="Тест письма",
    )

    smtp = MagicMock()
    smtp.is_connected = True
    smtp.connect = AsyncMock()
    smtp.login = AsyncMock()
    smtp.send_message = AsyncMock()
    smtp.quit = AsyncMock()

    with patch("app.services.email.aiosmtplib.SMTP", return_value=smtp):
        sent = await service.send_contact_emails(payload)

    assert sent is True
    assert smtp.send_message.await_count == 2
    print("OK: both emails sent via mocked SMTP")


async def check_second_failure_is_502() -> None:
    """Падение второго письма даёт ExternalServiceError (общий fail)"""
    settings = _settings(
        smtp_host="smtp.example.com",
        mail_from="noreply@example.com",
        mail_to_owner="owner@example.com",
        smtp_use_tls=True,
    )
    service = EmailService(settings)
    payload = ContactRequest(
        name="Иван Иванов",
        phone="+79991234567",
        email="ivan@example.com",
        comment="Тест",
    )

    smtp = MagicMock()
    smtp.is_connected = True
    smtp.connect = AsyncMock()
    smtp.login = AsyncMock()
    smtp.send_message = AsyncMock(side_effect=[None, RuntimeError("user send failed")])
    smtp.quit = AsyncMock()

    with patch("app.services.email.aiosmtplib.SMTP", return_value=smtp):
        try:
            await service.send_contact_emails(payload)
            raise AssertionError("expected ExternalServiceError")
        except ExternalServiceError as exc:
            assert exc.status_code == 502
            assert exc.code == "email_send_failed"
    print("OK: second email failure -> 502 email_send_failed")


def check_api_without_smtp() -> None:
    """POST /api/contact без SMTP в development возвращает 201 и email_sent=false"""
    clear_settings_cache()
    client = TestClient(app)
    response = client.post(
        "/api/contact",
        json={
            "name": "Иван Иванов",
            "phone": "+79991234567",
            "email": "ivan@example.com",
            "comment": "Проверка API",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email_sent"] is False
    assert "email" in body["message"].lower() or "SMTP" in body["message"] or "принят" in body["message"]
    print("OK: API 201 with email_sent=false when SMTP unset")


async def main() -> None:
    await check_skip_when_unconfigured()
    await check_send_both_via_mock()
    await check_second_failure_is_502()
    check_api_without_smtp()
    print("All email smoke checks passed")


if __name__ == "__main__":
    asyncio.run(main())
