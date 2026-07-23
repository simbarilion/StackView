"""Тесты AI-слоя: классификация, тональность, черновик ответа"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.ai import (
    AIAnalysisResult,
    AIEnrichment,
    RequestClassification,
    SentimentAnalysis,
)
from app.services.ai import AIService


@pytest.mark.asyncio
async def test_enrich_skipped_when_ai_not_configured(disabled_ai_settings) -> None:
    """Без API-ключа enrich сразу возвращает ai_available=false"""
    service = AIService(disabled_ai_settings)
    result = await service.enrich("Хочу сотрудничать", name="Иван")
    assert result.ai_available is False
    assert result.ai_analysis is None
    assert result.suggested_reply is None


def test_ai_client_uses_custom_base_url(configured_ai_settings) -> None:
    """OPENAI_BASE_URL пробрасывается в AsyncOpenAI"""
    settings = configured_ai_settings.model_copy(
        update={"openai_base_url": "https://api.groq.com/openai/v1"},
    )
    with patch("app.services.ai.AsyncOpenAI") as mock_client:
        AIService(settings)
    mock_client.assert_called_once_with(
        api_key="sk-test-key",
        base_url="https://api.groq.com/openai/v1",
    )


def test_ai_client_default_without_base_url(configured_ai_settings) -> None:
    """Без OPENAI_BASE_URL клиент создаётся только с api_key"""
    with patch("app.services.ai.AsyncOpenAI") as mock_client:
        AIService(configured_ai_settings)
    mock_client.assert_called_once_with(api_key="sk-test-key")


@pytest.mark.asyncio
async def test_classify_request_success(configured_ai_service: AIService) -> None:
    """classify_request парсит JSON от OpenAI в RequestClassification"""
    with patch.object(
        configured_ai_service,
        "_chat_json",
        AsyncMock(
            return_value={
                "category": "collaboration",
                "category_label": "Сотрудничество",
            }
        ),
    ):
        result = await configured_ai_service.classify_request("Давайте сделаем проект")

    assert result is not None
    assert result.category == "collaboration"
    assert result.category_label == "Сотрудничество"


@pytest.mark.asyncio
async def test_analyze_sentiment_success(configured_ai_service: AIService) -> None:
    """analyze_sentiment парсит тональность и score"""
    with patch.object(
        configured_ai_service,
        "_chat_json",
        AsyncMock(return_value={"sentiment": "positive", "sentiment_score": 0.75}),
    ):
        result = await configured_ai_service.analyze_sentiment("Отличная идея!")

    assert result is not None
    assert result.sentiment == "positive"
    assert result.sentiment_score == 0.75


@pytest.mark.asyncio
async def test_generate_suggested_reply_success(configured_ai_service: AIService) -> None:
    """generate_suggested_reply возвращает текст черновика"""
    with patch.object(
        configured_ai_service,
        "_chat_json",
        AsyncMock(return_value={"suggested_reply": "Здравствуйте, спасибо за сообщение!"}),
    ):
        result = await configured_ai_service.generate_suggested_reply(
            "Хочу обсудить проект",
            name="Иван",
        )

    assert result == "Здравствуйте, спасибо за сообщение!"


@pytest.mark.asyncio
async def test_classify_returns_none_on_timeout(configured_ai_service: AIService) -> None:
    """Таймаут OpenAI для classify даёт None, без исключения наружу"""
    with patch.object(
        configured_ai_service,
        "_chat_json",
        AsyncMock(side_effect=asyncio.TimeoutError),
    ):
        result = await configured_ai_service.classify_request("текст")
    assert result is None


@pytest.mark.asyncio
async def test_enrich_all_functions_fail(configured_ai_service: AIService) -> None:
    """Если все три функции упали — ai_available=false"""
    with (
        patch.object(configured_ai_service, "classify_request", AsyncMock(return_value=None)),
        patch.object(configured_ai_service, "analyze_sentiment", AsyncMock(return_value=None)),
        patch.object(configured_ai_service, "generate_suggested_reply", AsyncMock(return_value=None)),
    ):
        result = await configured_ai_service.enrich("комментарий", name="Иван")

    assert result.ai_available is False


@pytest.mark.asyncio
async def test_enrich_partial_success_one_function(configured_ai_service: AIService) -> None:
    """Успех хотя бы одной функции — ai_available=true и только успешные поля"""
    classification = RequestClassification(
        category="question",
        category_label="Вопрос",
    )
    with (
        patch.object(
            configured_ai_service,
            "classify_request",
            AsyncMock(return_value=classification),
        ),
        patch.object(configured_ai_service, "analyze_sentiment", AsyncMock(return_value=None)),
        patch.object(configured_ai_service, "generate_suggested_reply", AsyncMock(return_value=None)),
    ):
        result = await configured_ai_service.enrich("У меня вопрос", name="Иван")

    assert result.ai_available is True
    assert result.ai_analysis is not None
    assert result.ai_analysis.category == "question"
    assert result.ai_analysis.sentiment is None
    assert result.suggested_reply is None


@pytest.mark.asyncio
async def test_enrich_full_success(configured_ai_service: AIService) -> None:
    """Все три функции успешны — полный AIEnrichment"""
    with (
        patch.object(
            configured_ai_service,
            "classify_request",
            AsyncMock(
                return_value=RequestClassification(
                    category="job",
                    category_label="Вакансия / работа",
                )
            ),
        ),
        patch.object(
            configured_ai_service,
            "analyze_sentiment",
            AsyncMock(return_value=SentimentAnalysis(sentiment="neutral", sentiment_score=0.1)),
        ),
        patch.object(
            configured_ai_service,
            "generate_suggested_reply",
            AsyncMock(return_value="Черновик ответа от AI"),
        ),
    ):
        result = await configured_ai_service.enrich("Ищу работу", name="Иван")

    assert result.ai_available is True
    assert result.ai_analysis is not None
    assert result.ai_analysis.category == "job"
    assert result.ai_analysis.sentiment == "neutral"
    assert result.suggested_reply == "Черновик ответа от AI"


def test_format_for_email_with_analysis_and_reply() -> None:
    """format_for_email собирает текстовый блок для письма владельцу"""
    enrichment = AIEnrichment(
        ai_available=True,
        ai_analysis=AIAnalysisResult(
            category="collaboration",
            category_label="Сотрудничество",
            sentiment="positive",
            sentiment_score=0.9,
        ),
        suggested_reply="Спасибо за интерес!",
    )
    text = enrichment.format_for_email()
    assert text is not None
    assert "Сотрудничество" in text
    assert "positive" in text
    assert "Спасибо за интерес!" in text


def test_format_for_email_when_unavailable() -> None:
    """Без AI format_for_email возвращает None"""
    enrichment = AIEnrichment(ai_available=False)
    assert enrichment.format_for_email() is None


def test_api_contact_with_ai_success(
    client: TestClient,
    valid_payload: dict[str, str],
    mock_email_ok: AsyncMock,
    mock_ai_ok: AsyncMock,
) -> None:
    """POST /api/contact при успешном AI: 201 и ai_available=true"""
    response = client.post("/api/contact", json=valid_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["ai_available"] is True
    assert body["ai_analysis"]["category"] == "collaboration"
    assert body["suggested_reply"] is not None
    assert body["email_sent"] is True


def test_api_contact_when_ai_unavailable_still_succeeds(
    client: TestClient,
    valid_payload: dict[str, str],
    mock_email_ok: AsyncMock,
    mock_ai_unavailable: AsyncMock,
) -> None:
    """Если AI недоступен, contact всё равно 201 с ai_available=false"""
    response = client.post("/api/contact", json=valid_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["ai_available"] is False
    assert body["ai_analysis"] is None
    assert body["suggested_reply"] is None
    assert body["email_sent"] is True
