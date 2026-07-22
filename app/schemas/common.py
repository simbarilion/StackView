"""Общие схемы ответов API"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Единый формат ответа об ошибке"""

    code: str
    message: str
    details: Any = None
    request_id: str | None = None


class MessageResponse(BaseModel):
    """Простой ответ с текстовым сообщением"""

    message: str = Field(..., examples=["ok"])
