"""Схемы результатов AI-анализа обращения"""

from typing import Literal

from pydantic import BaseModel, Field


class RequestClassification(BaseModel):
    """Результат классификации типа обращения"""

    category: Literal["job", "collaboration", "question", "other"]
    category_label: str


class SentimentAnalysis(BaseModel):
    """Результат анализа тональности"""

    sentiment: Literal["positive", "neutral", "negative"]
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)


class AIAnalysisResult(BaseModel):
    """Частичный или полный AI-разбор для API-ответа (только успешные поля)"""

    category: str | None = None
    category_label: str | None = None
    sentiment: str | None = None
    sentiment_score: float | None = None


class AIEnrichment(BaseModel):
    """Итог обогащения обращения: доступность AI, анализ и черновик ответа"""

    ai_available: bool
    ai_analysis: AIAnalysisResult | None = None
    suggested_reply: str | None = None

    def format_for_email(self) -> str | None:
        """Собирает текстовый блок для письма владельцу или None, если данных нет"""
        if not self.ai_available:
            return None

        lines: list[str] = []
        if self.ai_analysis is not None:
            analysis = self.ai_analysis
            if analysis.category is not None:
                label = analysis.category_label or analysis.category
                lines.append(f"Категория: {label} ({analysis.category})")
            if analysis.sentiment is not None:
                score = f" ({analysis.sentiment_score:.2f})" if analysis.sentiment_score is not None else ""
                lines.append(f"Тональность: {analysis.sentiment}{score}")
        if self.suggested_reply:
            if lines:
                lines.append("")
            lines.append("Черновик ответа:")
            lines.append(self.suggested_reply)

        return "\n".join(lines) if lines else None
