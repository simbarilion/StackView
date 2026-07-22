"""Сервис обработки обращений с формы обратной связи"""

from app.schemas.contact import ContactRequest, ContactResponse


class ContactService:
    """Оркестрирует сценарий обращения"""

    async def submit(self, payload: ContactRequest) -> ContactResponse:
        """Принимает провалидированное обращение и возвращает подтверждение"""
        return ContactResponse(
            status="accepted",
            message="Обращение принято",
            name=payload.name,
            phone=payload.phone,
            email=str(payload.email),
            comment=payload.comment,
        )
