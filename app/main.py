"""Точка входа FastAPI-приложения"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import get_engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    engine = get_engine()
    if engine is not None:
        await engine.dispose()  # закрывает пулл соединений с PostgreSQL при завершении работы приложения


app = FastAPI(
    lifespan=lifespan,
)
