"""Сервис AI-анализа обращений через OpenAI."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, cast

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params.response_format_json_object import ResponseFormatJSONObject

from app.core.ai_prompts import (
    CATEGORY_LABELS,
    CLASSIFY_SYSTEM_PROMPT,
    SENTIMENT_SYSTEM_PROMPT,
    SUGGESTED_REPLY_SYSTEM_PROMPT,
)
from app.core.config import Settings
from app.schemas.ai import (
    AIAnalysisResult,
    AIEnrichment,
    RequestClassification,
    SentimentAnalysis,
)

logger = logging.getLogger(__name__)


class AIService:
    """Три AI-функции (классификация, тональность, черновик ответа) с graceful fallback."""

    def __init__(self, settings: Settings) -> None:
        """Сохраняет настройки и при необходимости создаёт клиент OpenAI."""
        self._settings = settings
        self._client: AsyncOpenAI | None = None
        if self.is_configured:
            client_kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
            if settings.openai_base_url:
                client_kwargs["base_url"] = settings.openai_base_url
            self._client = AsyncOpenAI(**client_kwargs)
            logger.info(
                "AI client ready: model=%s base_url=%s",
                settings.openai_model,
                settings.openai_base_url,
            )

    @property
    def is_configured(self) -> bool:
        """Проверяет, включён ли AI и задан ли API-ключ."""
        return bool(self._settings.ai_enabled and self._settings.openai_api_key)

    async def classify_request(self, comment: str) -> RequestClassification | None:
        """Классифицирует тип обращения. При ошибке/таймауте возвращает None."""
        if not self.is_configured or self._client is None:
            return None

        try:
            raw = await self._chat_json(CLASSIFY_SYSTEM_PROMPT, comment)
            category = str(raw.get("category", "other")).lower()
            if category not in CATEGORY_LABELS:
                category = "other"
            label = str(raw.get("category_label") or CATEGORY_LABELS[category])
            return cast(
                RequestClassification,
                RequestClassification.model_validate(
                    {"category": category, "category_label": label},
                ),
            )
        except Exception:
            logger.warning("AI classify_request failed", exc_info=True)
            return None

    async def analyze_sentiment(self, comment: str) -> SentimentAnalysis | None:
        """Определяет тональность комментария. При ошибке/таймауте возвращает None."""
        if not self.is_configured or self._client is None:
            return None

        try:
            raw = await self._chat_json(SENTIMENT_SYSTEM_PROMPT, comment)
            sentiment = str(raw.get("sentiment", "neutral")).lower()
            if sentiment not in {"positive", "neutral", "negative"}:
                sentiment = "neutral"
            score = float(raw.get("sentiment_score", 0.0))
            score = max(-1.0, min(1.0, score))
            return cast(
                SentimentAnalysis,
                SentimentAnalysis.model_validate(
                    {"sentiment": sentiment, "sentiment_score": score},
                ),
            )
        except Exception:
            logger.warning("AI analyze_sentiment failed", exc_info=True)
            return None

    async def generate_suggested_reply(
        self,
        comment: str,
        *,
        name: str,
        classification: RequestClassification | None = None,
        sentiment: SentimentAnalysis | None = None,
    ) -> str | None:
        """Генерирует черновик ответа через OpenAI. При ошибке/таймауте возвращает None."""
        if not self.is_configured or self._client is None:
            return None

        context_parts = [f"Имя отправителя: {name}", f"Комментарий: {comment}"]
        if classification is not None:
            context_parts.append(f"Категория: {classification.category_label} ({classification.category})")
        if sentiment is not None:
            context_parts.append(f"Тональность: {sentiment.sentiment} ({sentiment.sentiment_score:.2f})")

        try:
            raw = await self._chat_json(SUGGESTED_REPLY_SYSTEM_PROMPT, "\n".join(context_parts))
            reply = str(raw.get("suggested_reply", "")).strip()
            return reply or None
        except Exception:
            logger.warning("AI generate_suggested_reply failed", exc_info=True)
            return None

    async def enrich(self, comment: str, *, name: str) -> AIEnrichment:
        """
        Запускает AI-функции с независимым fallback.

        Сначала параллельно classify + sentiment, затем generate_suggested_reply
        (с учётом того, что уже удалось). ai_available=True, если успешна ≥1 функция.
        """
        if not self.is_configured:
            logger.info("AI отключён или нет API-ключа — пропускаем обогащение")
            return AIEnrichment(ai_available=False)

        classification_result, sentiment_result = await asyncio.gather(
            self.classify_request(comment),
            self.analyze_sentiment(comment),
        )
        suggested_reply = await self.generate_suggested_reply(
            comment,
            name=name,
            classification=classification_result,
            sentiment=sentiment_result,
        )

        if classification_result is None and sentiment_result is None and suggested_reply is None:
            return AIEnrichment(ai_available=False)

        analysis: AIAnalysisResult | None = None
        if classification_result is not None or sentiment_result is not None:
            category: str | None = None
            category_label: str | None = None
            sentiment_label: str | None = None
            sentiment_score: float | None = None

            if classification_result is not None:
                category = classification_result.category
                category_label = classification_result.category_label
            if sentiment_result is not None:
                sentiment_label = sentiment_result.sentiment
                sentiment_score = sentiment_result.sentiment_score

            analysis = AIAnalysisResult(
                category=category,
                category_label=category_label,
                sentiment=sentiment_label,
                sentiment_score=sentiment_score,
            )

        return AIEnrichment(
            ai_available=True,
            ai_analysis=analysis,
            suggested_reply=suggested_reply,
        )

    async def _chat_json(self, system_prompt: str, user_text: str) -> dict[str, Any]:
        """Выполняет один chat.completions-запрос с JSON-ответом и таймаутом на вызов."""
        client = self._client
        if client is None:
            raise RuntimeError("OpenAI client is not configured")

        messages: list[ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=system_prompt),
            ChatCompletionUserMessageParam(role="user", content=user_text),
        ]
        response_format: ResponseFormatJSONObject = {"type": "json_object"}

        async def _call() -> dict[str, Any]:
            response = await client.chat.completions.create(
                model=self._settings.openai_model,
                messages=messages,
                response_format=response_format,
                temperature=0.2,
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("OpenAI returned non-object JSON")
            return data

        return await asyncio.wait_for(_call(), timeout=self._settings.ai_timeout_seconds)
