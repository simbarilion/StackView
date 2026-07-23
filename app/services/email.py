"""Сервис отправки email-уведомлений по обращениям"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.schemas.contact import ContactRequest

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"


class EmailService:
    """Отправляет письма владельцу сайта и копию отправителю"""

    def __init__(self, settings: Settings) -> None:
        """Сохраняет настройки и инициализирует Jinja2-окружение шаблонов"""
        self._settings = settings
        self._jinja = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(enabled_extensions=("html", "xml")),
        )

    @property
    def is_configured(self) -> bool:
        """Проверяет, заданы ли обязательные SMTP-параметры"""
        return bool(self._settings.smtp_host and self._settings.mail_from and self._settings.mail_to_owner)

    async def send_contact_emails(
        self,
        payload: ContactRequest,
        *,
        ai_analysis: str | None = None,
    ) -> bool:
        """
        Отправляет письмо владельцу и копию пользователю атомарно в рамках одной SMTP-сессии.
        Returns:
            True — оба письма отправлены; False — SMTP не настроен (только development).
        Raises:
            ExternalServiceError: SMTP не настроен в production или сбой отправки
        """
        if not self.is_configured:
            if self._settings.app_env == "production":
                raise ExternalServiceError(
                    "Email service is not configured",
                    code="email_not_configured",
                )
            logger.warning(
                "SMTP не настроен — пропускаем отправку писем (env=%s)",
                self._settings.app_env,
            )
            return False

        context = self._build_context(payload, ai_analysis=ai_analysis)
        owner_message = self._build_owner_message(payload, context)
        user_message = self._build_user_message(payload, context)

        try:
            await self._send_both(owner_message, user_message)
        except ExternalServiceError:
            raise
        except Exception as exc:
            logger.exception("Ошибка отправки писем")
            raise ExternalServiceError(
                "Failed to send contact emails",
                code="email_send_failed",
                details={"reason": str(exc)},
            ) from exc

        logger.info(
            "Contact emails sent: owner=%s user=%s",
            self._settings.mail_to_owner,
            payload.email,
        )
        return True

    def _build_context(
        self,
        payload: ContactRequest,
        *,
        ai_analysis: str | None,
    ) -> dict[str, Any]:
        """Формирует общий контекст для шаблонов писем"""
        return {
            "app_name": self._settings.app_name,
            "name": payload.name,
            "phone": payload.phone,
            "email": str(payload.email),
            "comment": payload.comment,
            "submitted_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ai_analysis": ai_analysis,
        }

    def _render(self, template_name: str, context: dict[str, Any]) -> str:
        """Рендерит шаблон Jinja2 с переданным контекстом"""
        return str(self._jinja.get_template(template_name).render(**context))

    def _build_owner_message(
        self,
        payload: ContactRequest,
        context: dict[str, Any],
    ) -> EmailMessage:
        """Собирает MIME-письмо для владельца сайта"""
        subject = f"[{self._settings.app_name}] Новое обращение от {payload.name}"
        text_body = self._render("owner_notification.txt", context)
        html_body = self._render("owner_notification.html", context)

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._settings.mail_from
        message["To"] = self._settings.mail_to_owner
        message["Reply-To"] = str(payload.email)
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")
        return message

    def _build_user_message(
        self,
        payload: ContactRequest,
        context: dict[str, Any],
    ) -> EmailMessage:
        """Собирает MIME-письмо-подтверждение для отправителя"""
        subject = f"Мы получили ваше сообщение — {self._settings.app_name}"
        text_body = self._render("user_confirmation.txt", context)
        html_body = self._render("user_confirmation.html", context)

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._settings.mail_from
        message["To"] = str(payload.email)
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")
        return message

    async def _send_both(self, owner_message: EmailMessage, user_message: EmailMessage) -> None:
        """
        Отправляет оба письма в одной SMTP-сессии.
        Если второе письмо падает после успешного первого — это общий fail (502):
        откатить уже отправленное SMTP-письмо нельзя.
        """
        assert self._settings.smtp_host is not None
        assert self._settings.mail_from is not None

        smtp = aiosmtplib.SMTP(
            hostname=self._settings.smtp_host,
            port=self._settings.smtp_port,
            use_tls=self._settings.smtp_use_ssl,
            start_tls=self._settings.smtp_use_tls,
        )
        try:
            await smtp.connect()
            if self._settings.smtp_username and self._settings.smtp_password:
                await smtp.login(self._settings.smtp_username, self._settings.smtp_password)

            await smtp.send_message(owner_message)
            await smtp.send_message(user_message)
        except Exception as exc:
            logger.exception("Сбой SMTP при отправке пары contact-писем")
            raise ExternalServiceError(
                "Failed to send contact emails",
                code="email_send_failed",
                details={"reason": str(exc)},
            ) from exc
        finally:
            if smtp.is_connected:
                await smtp.quit()
