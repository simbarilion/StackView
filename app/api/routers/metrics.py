"""Эндпоинт статистики обращений"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_contact_repository
from app.repositories.contact import ContactRepository
from app.schemas.common import ErrorResponse
from app.schemas.metrics import MetricsResponse

router = APIRouter(tags=["metrics"])


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Статистика обращений",
    description=(
        "Возвращает агрегаты по таблице `contact_submissions`: "
        "общее число, сколько с email/AI, группировки по category и sentiment."
    ),
    responses={
        200: {"description": "Агрегаты из PostgreSQL"},
        502: {"description": "БД недоступна", "model": ErrorResponse},
    },
)
async def get_metrics(
    repository: ContactRepository = Depends(get_contact_repository),
) -> MetricsResponse:
    """Возвращает счётчики обращений из PostgreSQL"""
    return await repository.get_metrics()
