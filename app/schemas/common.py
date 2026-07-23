"""Общие схемы ответов API"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Единый формат ответа об ошибке"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "code": "rate_limit_exceeded",
                    "message": "Слишком много запросов. Попробуйте позже.",
                    "details": {"retry_after_seconds": 60},
                    "request_id": "a1b2c3d4",
                },
                {
                    "code": "validation_error",
                    "message": "Ошибка валидации запроса",
                    "details": [{"loc": ["body", "email"], "msg": "value is not a valid email address"}],
                    "request_id": "e5f6g7h8",
                },
            ]
        }
    )
    code: str = Field(..., description="Код ошибки", examples=["rate_limit_exceeded"])
    message: str = Field(..., description="Описание")
    details: Any = Field(default=None, description="Дополнительные данные об ошибке")
    request_id: str | None = Field(default=None, description="Идентификатор запроса из логов")


class MessageResponse(BaseModel):
    """Простой ответ с текстовым сообщением"""

    message: str = Field(..., examples=["ok"])
