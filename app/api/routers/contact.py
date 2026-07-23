"""Эндпоинты формы обратной связи"""

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import enforce_contact_rate_limit, get_contact_service
from app.schemas.common import ErrorResponse
from app.schemas.contact import ContactRequest, ContactResponse
from app.services.contact import ContactService

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить обращение",
    description=(
        "Принимает данные формы обратной связи: санитизация и валидация полей, "
        "rate limit по IP, AI-обогащение (категория, тональность, черновик ответа), "
        "отправка писем владельцу и пользователю, сохранение в PostgreSQL.\n\n"
        "- Сбой AI не приводит к 502: ответ с `ai_available=false`.\n"
        "- Сбой SMTP или БД — HTTP 502."
    ),
    responses={
        201: {"description": "Обращение принято"},
        422: {"description": "Ошибка валидации", "model": ErrorResponse},
        429: {"description": "Превышен rate limit", "model": ErrorResponse},
        502: {"description": "Ошибка email или БД", "model": ErrorResponse},
    },
    dependencies=[Depends(enforce_contact_rate_limit)],
)
async def create_contact(
    payload: ContactRequest,
    request: Request,
    contact_service: ContactService = Depends(get_contact_service),
) -> ContactResponse:
    """Принимает данные формы, валидирует их и передаёт в сервис"""
    client_ip = request.client.host if request.client else None
    return await contact_service.submit(payload, client_ip=client_ip)
