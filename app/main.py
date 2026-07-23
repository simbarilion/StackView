"""Точка входа FastAPI-приложения"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.api.routers import pages
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.db.session import get_engine, init_db

_STATIC_DIR = Path(__file__).resolve().parent / "static"

logger = logging.getLogger(__name__)
settings = get_settings()
setup_logging(settings)

OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Проверка работоспособности сервиса.",
    },
    {
        "name": "contact",
        "description": (
            "Форма обратной связи: валидация, rate limit, AI-обогащение, отправка email и сохранение в PostgreSQL."
        ),
    },
    {
        "name": "metrics",
        "description": "Агрегированная статистика сохранённых обращений из БД.",
    },
]

API_DESCRIPTION = """
Backend для формы обратной связи на лендинге разработчика.

**Основные сценарии**
- `POST /api/contact` — принять обращение, обогатить через OpenAI, отправить письма, сохранить в БД
- `GET /api/metrics` — счётчики и группировки по категории / тональности
- `GET /api/health` — healthcheck

**Ограничения**
- Rate limit по IP (файл `data/rate_limit.json`, настройки `RATE_LIMIT_*`)
- При сбое SMTP или БД — HTTP 502; сбой AI не блокирует приём (флаг `ai_available`)
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.log_dir).mkdir(parents=True, exist_ok=True)

    init_db(settings)
    logger.info("Application started")
    yield

    engine = get_engine()
    if engine is not None:
        await engine.dispose()  # закрывает пулл соединений с PostgreSQL при завершении работы приложения
    logger.info("Application stopped")


app = FastAPI(
    title="StackView API",
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    contact={
        "name": "Popova Nadezhda",
        "email": "nadezhdapopova13@yandex.ru",
    },
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)

app.include_router(pages.router)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
