"""Схемы запроса и ответа формы обратной связи"""

import re
from html import unescape

from pydantic import BaseModel, EmailStr, Field, field_validator

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

    name: str = Field(..., min_length=2, max_length=100, examples=["Иван Иванов"])
    phone: str = Field(..., min_length=5, max_length=32, examples=["+79991234567"])
    email: EmailStr = Field(..., examples=["ivan@example.com"])
    comment: str = Field(..., min_length=1, max_length=2000, examples=["Хочу обсудить проект"])

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

    status: str = Field(..., examples=["accepted"])
    message: str
    name: str
    phone: str
    email: str
    comment: str
    email_sent: bool = Field(..., description="True, если оба письма успешно отправлены")
