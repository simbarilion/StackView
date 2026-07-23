"""Схемы ответов health-эндпоинта"""

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Ответ проверки состояния сервиса"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "service": "StackView",
                    "environment": "development",
                }
            ]
        }
    )
    status: str = Field(..., description="Статус сервиса", examples=["ok"])
    service: str = Field(..., description="Имя приложения", examples=["StackView"])
    environment: str = Field(..., description="Окружение (APP_ENV)", examples=["development"])
