"""Эндпоинты формы обратной связи."""

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import enforce_contact_rate_limit, get_contact_service
from app.schemas.contact import ContactRequest, ContactResponse
from app.services.contact import ContactService

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить обращение",
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
