"""Общие зависимости FastAPI"""

from app.core.config import Settings, get_settings
from app.services.contact import ContactService


def settings_dep() -> Settings:
    """Возвращает настройки приложения для внедрения через Depends"""
    return get_settings()


def get_contact_service() -> ContactService:
    """Возвращает объект оркестратора обращения ContactService"""
    return ContactService()
