"""Схемы запроса и ответа формы обратной связи"""

import re
from html import unescape

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.ai import AIAnalysisResult

_TAG_RE = re.compile(r"<[^>]+>")
_PHONE_DIGITS_RE = re.compile(r"\D+")


def _sanitize_text(value: str) -> str:
    """Удаляет HTML-теги, обрезает пробелы"""
    without_tags = _TAG_RE.sub("", unescape(value))
    return " ".join(without_tags.split()).strip()


def _normalize_phone(value: str) -> str:
    """Оставляет только цифры и ведущий плюс"""
    cleaned = value.strip()
    has_plus = cleaned.startswith("+")
    digits = _PHONE_DIGITS_RE.sub("", cleaned)
    return f"+{digits}" if has_plus else digits


class ContactRequest(BaseModel):
    """Входящие данные формы обратной связи"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Иван Иванов",
                    "phone": "+79991234567",
                    "email": "ivan@example.com",
                    "comment": "Хочу обсудить проект по FastAPI и интеграции с CRM.",
                }
            ]
        }
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Имя отправителя (HTML удаляется)",
        examples=["Иван Иванов"],
    )
    phone: str = Field(
        ...,
        min_length=5,
        max_length=32,
        description="Телефон: 10–15 цифр, допускается ведущий «+»",
        examples=["+79991234567"],
    )
    email: EmailStr = Field(
        ...,
        description="Email для ответа и копии письма",
        examples=["ivan@example.com"],
    )
    comment: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Текст обращения (HTML удаляется)",
        examples=["Хочу обсудить проект"],
    )

    @field_validator("name", "comment", mode="before")
    @classmethod
    def sanitize_text_fields(cls, value: object) -> object:
        """Санитизирует текстовые поля от HTML и лишних пробелов"""
        if isinstance(value, str):
            return _sanitize_text(value)
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def sanitize_phone(cls, value: object) -> object:
        """Нормализует телефон к виду +цифры или цифры"""
        if isinstance(value, str):
            return _normalize_phone(value)
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone_digits(cls, value: str) -> str:
        """Проверяет, что в телефоне достаточно цифр"""
        digits = re.sub(r"\D", "", value)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Телефон должен содержать от 10 до 15 цифр")
        return value


class ContactResponse(BaseModel):
    """Ответ на успешную отправку формы"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "accepted",
                    "message": "Обращение принято",
                    "name": "Иван Иванов",
                    "phone": "+79991234567",
                    "email": "ivan@example.com",
                    "comment": "Хочу обсудить проект",
                    "email_sent": True,
                    "ai_available": True,
                    "ai_analysis": {
                        "category": "collaboration",
                        "category_label": "Сотрудничество",
                        "sentiment": "positive",
                        "sentiment_score": 0.75,
                    },
                    "suggested_reply": "Спасибо за обращение! Предлагаю созвониться на этой неделе.",
                }
            ]
        }
    )
    status: str = Field(..., description="Статус обработки", examples=["accepted"])
    message: str = Field(..., description="Человекочитаемое сообщение", examples=["Обращение принято"])
    name: str = Field(..., description="Имя из запроса")
    phone: str = Field(..., description="Нормализованный телефон")
    email: str = Field(..., description="Email из запроса")
    comment: str = Field(..., description="Комментарий из запроса")
    email_sent: bool = Field(..., description="True, если оба письма успешно отправлены")
    ai_available: bool = Field(..., description="True, если успешна хотя бы одна AI-функция")
    ai_analysis: AIAnalysisResult | None = Field(
        default=None,
        description="Частичный или полный AI-разбор (только успешные поля)",
    )
    suggested_reply: str | None = Field(
        default=None,
        description="Черновик ответа, сгенерированный OpenAI",
    )
