"""Репозиторий обращений в PostgreSQL"""

from __future__ import annotations

import logging

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ExternalServiceError
from app.models.contact import ContactSubmission
from app.schemas.ai import AIEnrichment
from app.schemas.contact import ContactRequest
from app.schemas.metrics import MetricsResponse

logger = logging.getLogger(__name__)


class ContactRepository:
    """Сохраняет обращения и отдаёт агрегированную статистику"""

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

    async def get_metrics(self) -> MetricsResponse:
        """Считает агрегаты по таблице contact_submissions БД"""
        try:
            totals_stmt = select(
                func.count(ContactSubmission.id),
                func.coalesce(
                    func.sum(case((ContactSubmission.email_sent.is_(True), 1), else_=0)),
                    0,
                ),
                func.coalesce(
                    func.sum(case((ContactSubmission.ai_available.is_(True), 1), else_=0)),
                    0,
                ),
            )
            total, email_sent_count, ai_available_count = (await self._session.execute(totals_stmt)).one()

            category_rows = (
                await self._session.execute(
                    select(ContactSubmission.category, func.count())
                    .where(ContactSubmission.category.is_not(None))
                    .group_by(ContactSubmission.category)
                )
            ).all()
            sentiment_rows = (
                await self._session.execute(
                    select(ContactSubmission.sentiment, func.count())
                    .where(ContactSubmission.sentiment.is_not(None))
                    .group_by(ContactSubmission.sentiment)
                )
            ).all()
        except Exception as exc:
            logger.exception("Не удалось получить метрики из БД")
            raise ExternalServiceError(
                "Failed to load contact metrics",
                code="database_error",
                details={"reason": str(exc)},
            ) from exc

        return MetricsResponse(
            total_submissions=int(total or 0),
            email_sent=int(email_sent_count or 0),
            ai_available=int(ai_available_count or 0),
            by_category={str(key): int(count) for key, count in category_rows if key is not None},
            by_sentiment={str(key): int(count) for key, count in sentiment_rows if key is not None},
        )
