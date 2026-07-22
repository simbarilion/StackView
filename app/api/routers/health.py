"""Эндпоинты проверки состояния сервиса"""

from fastapi import APIRouter, Depends

from app.api.dependencies import settings_dep
from app.core.config import Settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(settings_dep)) -> HealthResponse:
    """Возвращает статус работоспособности сервиса."""
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
    )
