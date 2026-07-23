"""Seed-скрипт: заполняет БД читаемыми демо-обращениями.
Запуск: poetry run seed
Требуется: настроенный .env (db_*) и применённые миграции (alembic upgrade head)
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory, init_db
from app.models.contact import ContactSubmission

logger = logging.getLogger(__name__)

SEED_SUBMISSIONS: list[dict[str, object]] = [
    {
        "name": "Анна Ковалёва",
        "phone": "+79031234567",
        "email": "anna.kovaleva@example.com",
        "comment": (
            "Здравствуйте! Рассматриваем кандидата на позицию backend-разработчика. Можем созвониться на этой неделе?"
        ),
        "email_sent": True,
        "ai_available": True,
        "category": "job",
        "sentiment": "positive",
        "sentiment_score": 0.82,
        "suggested_reply": (
            "Здравствуйте, Анна! Спасибо за интерес к сотрудничеству. "
            "Удобно созвониться во вторник или среду после 15:00."
        ),
        "client_ip": "203.0.113.10",
    },
    {
        "name": "Дмитрий Орлов",
        "phone": "+79161239876",
        "email": "d.orlov@startup.io",
        "comment": ("Хотим обсудить партнёрство: нужен API для лендинга и интеграция с CRM. Бюджет и сроки гибкие."),
        "email_sent": True,
        "ai_available": True,
        "category": "collaboration",
        "sentiment": "positive",
        "sentiment_score": 0.71,
        "suggested_reply": (
            "Дмитрий, спасибо за предложение! Пришлите, пожалуйста, краткое ТЗ — оценю объём и вернусь с вариантами."
        ),
        "client_ip": "198.51.100.22",
    },
    {
        "name": "Елена Смирнова",
        "phone": "+79265550123",
        "email": "elena.smirnova@mail.example",
        "comment": (
            "Подскажите, используете ли вы FastAPI и PostgreSQL в pet-проектах? "
            "Интересно сравнить подходы к миграциям."
        ),
        "email_sent": True,
        "ai_available": True,
        "category": "question",
        "sentiment": "neutral",
        "sentiment_score": 0.12,
        "suggested_reply": (
            "Елена, да — в демо-проекте StackView как раз FastAPI + Alembic + PostgreSQL. "
            "Могу кратко расписать структуру папок."
        ),
        "client_ip": "192.0.2.45",
    },
    {
        "name": "Игорь Васильев",
        "phone": "+79097778899",
        "email": "igor.v@example.org",
        "comment": "Форма на сайте долго не отвечала, письмо так и не пришло. Разочарован сервисом.",
        "email_sent": False,
        "ai_available": True,
        "category": "other",
        "sentiment": "negative",
        "sentiment_score": -0.64,
        "suggested_reply": ("Игорь, извините за сбой. Проверим логи SMTP и rate limit, ответим вручную на ваш email."),
        "client_ip": "203.0.113.77",
    },
    {
        "name": "Мария Петрова",
        "phone": "+79100001122",
        "email": "m.petrova@example.com",
        "comment": "Просто тестовое сообщение без особого контекста.",
        "email_sent": True,
        "ai_available": False,
        "category": None,
        "sentiment": None,
        "sentiment_score": None,
        "suggested_reply": None,
        "client_ip": "127.0.0.1",
    },
]


async def _seed() -> None:
    """Вставляет демо-записи, если таблица ещё пуста"""
    settings = get_settings()
    init_db(settings)

    session_factory = get_session_factory()
    if session_factory is None:
        raise RuntimeError("БД не инициализирована. Проверьте параметры DB_* в .env")

    try:
        async with session_factory() as session:
            existing = await session.scalar(select(func.count()).select_from(ContactSubmission))
            if existing and int(existing) > 0:
                print(f"Seed пропущен: в contact_submissions уже есть {existing} записей.")
                return

            for row in SEED_SUBMISSIONS:
                session.add(ContactSubmission(**row))
            await session.commit()
            print(f"Seed выполнен: добавлено {len(SEED_SUBMISSIONS)} обращений.")
    except ProgrammingError as exc:
        message = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        if "contact_submissions" in message or "does not exist" in message or "не существует" in message:
            raise RuntimeError(
                "Таблица contact_submissions не найдена. Сначала примените миграции: poetry run alembic upgrade head"
            ) from exc
        raise
    finally:
        engine = get_engine()
        if engine is not None:
            await engine.dispose()


def main() -> None:
    """Точка входа для `poetry run seed`"""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_seed())


if __name__ == "__main__":
    main()
