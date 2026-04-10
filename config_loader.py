"""Загрузка config.ini: путь задаётся через CONFIG_INI_PATH или каталог проекта."""

from __future__ import annotations

import os
from configparser import ConfigParser
from functools import lru_cache
from pathlib import Path


def _config_path() -> Path:
    env = (os.environ.get("CONFIG_INI_PATH") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent / "config.ini"


@lru_cache(maxsize=1)
def read_config() -> ConfigParser:
    path = _config_path()
    if path.is_dir():
        raise RuntimeError(
            f"{path} указывает на каталог, а не на файл. "
            "Часто так бывает, если в docker-compose смонтирован несуществующий config.ini — "
            "Docker создаёт папку. Удалите её на хосте и создайте настоящий файл config.ini."
        )
    if not path.is_file():
        raise RuntimeError(
            f"Файл конфигурации не найден: {path}. "
            "Создайте config.ini рядом с docker-compose на сервере, "
            "либо задайте CONFIG_INI_PATH, либо положите config.example.ini в образ и перезапустите (см. docker-entrypoint.sh)."
        )
    cfg = ConfigParser()
    loaded = cfg.read(path, encoding="utf-8")
    if not loaded:
        raise RuntimeError(f"Не удалось прочитать {path}")
    if not cfg.has_section("Postgres"):
        raise RuntimeError(
            f"В {path} нет секции [Postgres]. "
            "Скопируйте config.example.ini в config.ini и заполните параметры."
        )
    return cfg
