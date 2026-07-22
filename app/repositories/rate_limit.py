"""Файловое хранилище счётчиков rate limiting"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any


class RateLimitRepository:
    """Хранит fixed-window счётчики запросов в JSON-файле"""

    def __init__(self, file_path: Path) -> None:
        """Инициализирует репозиторий с путём к файлу состояния"""
        self._file_path = file_path
        self._lock = threading.Lock()

    def register_hit(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> bool:
        """
        Регистрирует попытку запроса для ключа (IP).
        Возвращает True, если запрос разрешён, False — если лимит исчерпан
        """
        timestamp = time.time() if now is None else now

        with self._lock:
            state = self._read_state()
            entry = state.get(key)

            if entry is None or timestamp - float(entry["window_start"]) >= window_seconds:
                state[key] = {"window_start": timestamp, "count": 1}
                self._write_state(state)
                return True

            count = int(entry["count"])
            if count >= limit:
                return False

            entry["count"] = count + 1
            state[key] = entry
            self._write_state(state)
            return True

    def seconds_until_reset(
        self,
        key: str,
        *,
        window_seconds: int,
        now: float | None = None,
    ) -> int:
        """Возвращает секунды до сброса окна для ключа (0, если окна нет)"""
        timestamp = time.time() if now is None else now
        with self._lock:
            state = self._read_state()
            entry = state.get(key)
            if entry is None:
                return 0
            elapsed = timestamp - float(entry["window_start"])
            remaining = int(window_seconds - elapsed)
            return max(remaining, 0)

    def _read_state(self) -> dict[str, Any]:
        """Читает состояние из JSON-файла"""
        if not self._file_path.exists():
            return {}
        try:
            raw = self._file_path.read_text(encoding="utf-8").strip()
            if not raw:
                return {}
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_state(self, state: dict[str, Any]) -> None:
        """Атомарно записывает состояние во временный файл и заменяет целевой"""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._file_path.with_suffix(self._file_path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(self._file_path)
