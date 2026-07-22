"""Агрегирующий API-роутер приложения"""

from fastapi import APIRouter

from app.api.routers import contact, health

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(contact.router)
