"""Сервис обработки обращений с формы обратной связи"""

from app.repositories.contact import ContactRepository
from app.schemas.contact import ContactRequest, ContactResponse
from app.services.ai import AIService
from app.services.email import EmailService


class ContactService:
    """Оркестрирует сценарий обращения: AI - email - сохранение - ответ"""

    def __init__(
        self,
        email_service: EmailService,
        ai_service: AIService,
        contact_repository: ContactRepository,
    ) -> None:
        """Принимает сервисы email/AI и репозиторий обращений"""
        self._email_service = email_service
        self._ai_service = ai_service
        self._contact_repository = contact_repository

    async def submit(
        self,
        payload: ContactRequest,
        *,
        client_ip: str | None = None,
    ) -> ContactResponse:
        """Обогащает обращение AI, отправляет письма, сохраняет в БД и возвращает ответ"""
        enrichment = await self._ai_service.enrich(payload.comment, name=payload.name)

        email_sent = await self._email_service.send_contact_emails(
            payload,
            ai_analysis=enrichment.format_for_email(),
        )

        await self._contact_repository.create(
            payload=payload,
            email_sent=email_sent,
            enrichment=enrichment,
            client_ip=client_ip,
        )

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
            ai_available=enrichment.ai_available,
            ai_analysis=enrichment.ai_analysis,
            suggested_reply=enrichment.suggested_reply,
        )
