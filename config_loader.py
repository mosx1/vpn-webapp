"""Загрузка config.ini из каталога проекта (не зависит от текущей рабочей директории — важно для Docker/gunicorn)."""

from __future__ import annotations

from configparser import ConfigParser
from functools import lru_cache
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent / "config.ini"


@lru_cache(maxsize=1)
def read_config() -> ConfigParser:
    cfg = ConfigParser()
    if not _CONFIG_PATH.is_file():
        raise RuntimeError(
            f"Файл конфигурации не найден: {_CONFIG_PATH}. "
            "В Docker смонтируйте config.ini (см. docker-compose volumes) и проверьте путь."
        )
    loaded = cfg.read(_CONFIG_PATH, encoding="utf-8")
    if not loaded:
        raise RuntimeError(f"Не удалось прочитать {_CONFIG_PATH}")
    if not cfg.has_section("Postgres"):
        raise RuntimeError(
            f"В {_CONFIG_PATH} нет секции [Postgres]. "
            "Скопируйте config.example.ini в config.ini и заполните параметры."
        )
    return cfg
