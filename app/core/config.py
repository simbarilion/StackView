import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "StackView"
    app_env: str = Field(default="development", description="development | production")
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # NoDecode: разрешает значения через запятую в .env
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])

    # Logs
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_file: str = "app.log"
    request_log_file: str = "requests.log"

    # Data
    data_dir: str = "data"

    # Database
    db_name: str
    db_user: str
    db_password: str
    db_host: str
    db_port: int = 5432

    # Ограничение частоты запросов
    rate_limit_requests: int = 5
    rate_limit_window_seconds: int = 60

    # SMTP
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    mail_from: str | None = None
    mail_to_owner: str | None = None

    # AI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = 15.0
    ai_enabled: bool = True

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

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


@lru_cache  # чтобы настройки не создавались при каждом импорте
def get_settings() -> Settings:
    """Возвращает закэшированный экземпляр настроек"""
    return Settings()


def clear_settings_cache() -> None:
    """Сбрасывает кэш настроек"""
    get_settings.cache_clear()
