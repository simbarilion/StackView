import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Self

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Корневая директория репозитория
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


def _to_asyncpg_url(url: str) -> str:
    """Приводит postgres/postgresql URL к виду для SQLAlchemy + asyncpg"""
    normalized = url.strip().replace("postgres://", "postgresql://", 1)
    if "+asyncpg://" not in normalized:
        normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)
    return normalized.replace("sslmode=require", "ssl=require")


def _to_psycopg2_url(url: str) -> str:
    """Приводит URL к виду для Alembic + psycopg2."""
    normalized = url.strip().replace("postgres://", "postgresql://", 1)
    normalized = normalized.replace("postgresql+asyncpg://", "postgresql://", 1)
    if "+psycopg2://" not in normalized:
        normalized = normalized.replace("postgresql://", "postgresql+psycopg2://", 1)
    return normalized


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения"""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "StackView"
    app_env: str = Field(default="development", description="development | production")
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, validation_alias=AliasChoices("APP_PORT", "PORT"))

    # NoDecode: разрешает значения через запятую в .env
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])

    # Logs
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_file: str = "app.log"
    request_log_file: str = "requests.log"

    # Data
    data_dir: str = "data"

    # Database: либо DATABASE_URL (Render), либо набор DB_* (локально)
    database_url_override: str | None = Field(default=None, validation_alias="DATABASE_URL")
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_host: str | None = None
    db_port: int = 5432

    # Ограничение частоты запросов
    rate_limit_requests: int = 5
    rate_limit_window_seconds: int = 60

    # SMTP
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False
    smtp_use_ssl: bool = True
    mail_from: str | None = None
    mail_to_owner: str | None = None

    # AI (OpenAI-compatible: OpenAI, Groq, OpenRouter, …)
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "llama-3.3-70b-versatile"
    ai_timeout_seconds: float = 15.0
    ai_enabled: bool = True

    @model_validator(mode="after")
    def validate_database_settings(self) -> Self:
        """Требует DATABASE_URL или полный набор DB_*."""
        if self.database_url_override and self.database_url_override.strip():
            return self
        missing = [
            name
            for name, value in (
                ("DB_NAME", self.db_name),
                ("DB_USER", self.db_user),
                ("DB_PASSWORD", self.db_password),
                ("DB_HOST", self.db_host),
            )
            if not value
        ]
        if missing:
            raise ValueError("Задайте DATABASE_URL или обязательные поля: " + ", ".join(missing))
        return self

    @property
    def database_url(self) -> str:
        """Асинхронный URL для SQLAlchemy + asyncpg"""
        if self.database_url_override and self.database_url_override.strip():
            return _to_asyncpg_url(self.database_url_override)
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_sync(self) -> str:
        """Синхронный URL для Alembic (psycopg2)"""
        if self.database_url_override and self.database_url_override.strip():
            return _to_psycopg2_url(self.database_url_override)
        return f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        """Разбирает CORS origins из строки JSON, списка через запятую или готового списка"""
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ["*"]
            if raw.startswith("["):
                return json.loads(raw)
            return [item.strip() for item in raw.split(",") if item.strip()]
        return value

    @field_validator("openai_base_url", "database_url_override", mode="before")
    @classmethod
    def empty_str_as_none(cls, value: object) -> object:
        """Пустую строку из .env трактует как None"""
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache  # чтобы настройки не создавались при каждом импорте
def get_settings() -> Settings:
    """Возвращает закэшированный экземпляр настроек"""
    return Settings()


def clear_settings_cache() -> None:
    """Сбрасывает кэш настроек"""
    get_settings.cache_clear()
