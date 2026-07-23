"""Схемы ответа метрик обращений"""

from pydantic import BaseModel, ConfigDict, Field


class MetricsResponse(BaseModel):
    """Статистика обращений (данные из БД)"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total_submissions": 5,
                    "email_sent": 4,
                    "ai_available": 4,
                    "by_category": {
                        "job": 1,
                        "collaboration": 1,
                        "question": 1,
                        "other": 1,
                    },
                    "by_sentiment": {
                        "positive": 2,
                        "neutral": 1,
                        "negative": 1,
                    },
                }
            ]
        }
    )
    total_submissions: int = Field(..., ge=0, description="Всего сохранённых обращений", examples=[5])
    email_sent: int = Field(..., ge=0, description="Обращений с успешной отправкой email", examples=[4])
    ai_available: int = Field(..., ge=0, description="Обращений с успешным AI-анализом", examples=[4])
    by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Число обращений по category (без NULL)",
        examples=[{"job": 1, "collaboration": 1}],
    )
    by_sentiment: dict[str, int] = Field(
        default_factory=dict,
        description="Число обращений по sentiment (без NULL)",
        examples=[{"positive": 2, "neutral": 1}],
    )
