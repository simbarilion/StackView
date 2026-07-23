"""Схемы ответа метрик обращений"""

from pydantic import BaseModel, Field


class MetricsResponse(BaseModel):
    """Статистика обращений (данные из БД)"""

    total_submissions: int = Field(..., ge=0, description="Всего сохранённых обращений")
    email_sent: int = Field(..., ge=0, description="Обращений с успешной отправкой email")
    ai_available: int = Field(..., ge=0, description="Обращений с успешным AI-анализом")
    by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Число обращений по category (без NULL)",
    )
    by_sentiment: dict[str, int] = Field(
        default_factory=dict,
        description="Число обращений по sentiment (без NULL)",
    )
