"""Тесты email-слоя"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_email_service
from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.main import app
from app.schemas.contact import ContactRequest
from app.services.email import EmailService


@pytest.mark.asyncio
async def test_send_skipped_when_smtp_not_configured(
    development_email_settings: Settings,
    contact_request: ContactRequest,
) -> None:
    """В development без SMTP отправка пропускается, возвращается False"""
    service = EmailService(development_email_settings)
    sent = await service.send_contact_emails(contact_request)
    assert sent is False


@pytest.mark.asyncio
async def test_send_raises_when_smtp_missing_in_production(
    production_email_settings: Settings,
    contact_request: ContactRequest,
) -> None:
    """В production без SMTP поднимается 502 email_not_configured"""
    service = EmailService(production_email_settings)
    with pytest.raises(ExternalServiceError) as exc_info:
        await service.send_contact_emails(contact_request)
    assert exc_info.value.status_code == 502
    assert exc_info.value.code == "email_not_configured"


@pytest.mark.asyncio
async def test_send_both_emails_via_smtp(
    configured_email_service: EmailService,
    contact_request: ContactRequest,
) -> None:
    """При настроенном SMTP оба письма уходят в одной сессии"""
    smtp = MagicMock()
    smtp.is_connected = True
    smtp.connect = AsyncMock()
    smtp.login = AsyncMock()
    smtp.send_message = AsyncMock()
    smtp.quit = AsyncMock()

    with patch("app.services.email.aiosmtplib.SMTP", return_value=smtp):
        sent = await configured_email_service.send_contact_emails(contact_request)

    assert sent is True
    assert smtp.connect.await_count == 1
    assert smtp.login.await_count == 1
    assert smtp.send_message.await_count == 2
    assert smtp.quit.await_count == 1

    owner_msg, user_msg = [call.args[0] for call in smtp.send_message.await_args_list]
    assert owner_msg["To"] == "owner@example.com"
    assert owner_msg["Reply-To"] == "ivan@example.com"
    assert user_msg["To"] == "ivan@example.com"


@pytest.mark.asyncio
async def test_second_email_failure_is_atomic_fail(
    configured_email_service: EmailService,
    contact_request: ContactRequest,
) -> None:
    """Падение второго письма даёт общий fail email_send_failed"""
    smtp = MagicMock()
    smtp.is_connected = True
    smtp.connect = AsyncMock()
    smtp.login = AsyncMock()
    smtp.send_message = AsyncMock(side_effect=[None, RuntimeError("user send failed")])
    smtp.quit = AsyncMock()

    with patch("app.services.email.aiosmtplib.SMTP", return_value=smtp):
        with pytest.raises(ExternalServiceError) as exc_info:
            await configured_email_service.send_contact_emails(contact_request)

    assert exc_info.value.status_code == 502
    assert exc_info.value.code == "email_send_failed"
    assert smtp.quit.await_count == 1


def test_api_contact_without_smtp_returns_email_sent_false(
    client: TestClient,
    development_email_settings: Settings,
    valid_payload: dict[str, str],
) -> None:
    """POST /api/contact без SMTP в development: 201 и email_sent=false"""
    app.dependency_overrides[get_email_service] = lambda: EmailService(development_email_settings)

    response = client.post("/api/contact", json=valid_payload)
    assert response.status_code == 201
    assert response.json()["email_sent"] is False


def test_api_contact_with_smtp_success(
    client: TestClient,
    valid_payload: dict[str, str],
    mock_email_ok: AsyncMock,
) -> None:
    """POST /api/contact при успешной отправке: 201 и email_sent=true"""
    response = client.post("/api/contact", json=valid_payload)
    assert response.status_code == 201
    assert response.json()["email_sent"] is True


def test_api_contact_smtp_failure_returns_502(
    client: TestClient,
    valid_payload: dict[str, str],
    mock_email_fail: AsyncMock,
) -> None:
    """POST /api/contact при сбое SMTP: 502 email_send_failed"""
    response = client.post("/api/contact", json=valid_payload)
    assert response.status_code == 502
    assert response.json()["code"] == "email_send_failed"
