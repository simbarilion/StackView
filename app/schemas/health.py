"""Схемы ответов health-эндпоинта"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Ответ проверки состояния сервиса"""

    status: str = Field(..., examples=["ok"])
    service: str
    environment: str
