"""Сервис обработки обращений с формы обратной связи"""

from app.schemas.contact import ContactRequest, ContactResponse
from app.services.email import EmailService


class ContactService:
    """Оркестрирует сценарий обращения"""

    def __init__(self, email_service: EmailService) -> None:
        """Принимает сервис отправки писем"""
        self._email_service = email_service

    async def submit(self, payload: ContactRequest) -> ContactResponse:
        """Принимает обращение, отправляет письма и возвращает подтверждение"""
        email_sent = await self._email_service.send_contact_emails(payload)

        if email_sent:
            message = "Обращение принято и отправлено на email"
        else:
            message = "Обращение принято (email не отправлен: SMTP не настроен)"

        return ContactResponse(
            status="accepted",
            message=message,
            name=payload.name,
            phone=payload.phone,
            email=str(payload.email),
            comment=payload.comment,
            email_sent=email_sent,
        )
