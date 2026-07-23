"""Репозиторий обращений в PostgreSQL"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ExternalServiceError
from app.models.contact import ContactSubmission
from app.schemas.ai import AIEnrichment
from app.schemas.contact import ContactRequest

logger = logging.getLogger(__name__)


class ContactRepository:
    """Сохраняет обращения и связанные флаги AI/email"""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает асинхронную сессию SQLAlchemy"""
        self._session = session

    async def create(
        self,
        *,
        payload: ContactRequest,
        email_sent: bool,
        enrichment: AIEnrichment,
        client_ip: str | None,
    ) -> ContactSubmission:
        """Создаёт запись обращения. При ошибке БД поднимает ExternalServiceError (502)"""
        analysis = enrichment.ai_analysis
        submission = ContactSubmission(
            name=payload.name,
            phone=payload.phone,
            email=str(payload.email),
            comment=payload.comment,
            email_sent=email_sent,
            ai_available=enrichment.ai_available,
            category=analysis.category if analysis else None,
            sentiment=analysis.sentiment if analysis else None,
            sentiment_score=analysis.sentiment_score if analysis else None,
            suggested_reply=enrichment.suggested_reply,
            client_ip=client_ip,
        )
        try:
            self._session.add(submission)
            await self._session.commit()
            await self._session.refresh(submission)
        except Exception as exc:
            await self._session.rollback()
            logger.exception("Не удалось сохранить обращение в БД")
            raise ExternalServiceError(
                "Failed to persist contact submission",
                code="database_error",
                details={"reason": str(exc)},
            ) from exc
        return submission
