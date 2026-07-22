"""Конфигурация логирования приложения"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import Settings


def setup_logging(settings: Settings) -> None:
    """Настраивает корневой логгер: консоль и файл, логгер запросов"""
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(log_level)

    # Избегаем дублирования handlers при reload
    if root.handlers:
        root.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_dir / settings.log_file,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Отдельный логгер запросов (только в файл) — используется middleware
    request_logger = logging.getLogger("app.requests")
    request_logger.setLevel(log_level)
    request_logger.propagate = False
    if not request_logger.handlers:
        request_handler = RotatingFileHandler(
            log_dir / settings.request_log_file,
            maxBytes=2_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        request_handler.setFormatter(formatter)
        request_logger.addHandler(request_handler)
