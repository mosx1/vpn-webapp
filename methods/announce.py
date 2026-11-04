import base64
from threading import Lock
from time import monotonic

from db.repository.app_settings import AppSettingsRepository
from db.models import AppSetting
from methods.interfaces import AppSettingsBase


class Annonce(AppSettingsBase):

    key: str = "subscription_announce_text"
    DEFAULT_SUBSCRIPTION_ANNOUNCE_TEXT = (
        "Личный кабинет переехал на сайт kuzmos.ru.\n"
    )
    _CACHE_TTL_SECONDS = 30.0
    _cache_lock = Lock()
    _cached_text: str | None = None
    _cached_header: str | None = None
    _cached_at: float = 0.0

    @classmethod
    def _cache_is_fresh(cls) -> bool:
        return (
            cls._cached_text is not None
            and monotonic() - cls._cached_at < cls._CACHE_TTL_SECONDS
        )

    @classmethod
    def invalidate_cache(cls) -> None:
        with cls._cache_lock:
            cls._cached_text = None
            cls._cached_header = None
            cls._cached_at = 0.0

    @classmethod
    def _store_cache(cls, text: str) -> str:
        encoded_announce = base64.b64encode(text.encode("utf-8")).decode("ascii")
        header_value = f"base64:{encoded_announce}"
        with cls._cache_lock:
            cls._cached_text = text
            cls._cached_header = header_value
            cls._cached_at = monotonic()
        return header_value

    @classmethod
    def _load_text(cls) -> str:
        with AppSettingsRepository() as app_settings_repo:
            announce_text = app_settings_repo.get_one(AppSetting.key == cls.key)
        if not announce_text:
            return cls.DEFAULT_SUBSCRIPTION_ANNOUNCE_TEXT
        return announce_text.value

    @classmethod
    def get_text(cls) -> str:
        with cls._cache_lock:
            if cls._cache_is_fresh():
                return cls._cached_text or cls.DEFAULT_SUBSCRIPTION_ANNOUNCE_TEXT
        text = cls._load_text()
        cls._store_cache(text)
        return text

    @classmethod
    def get_header_value(cls) -> str:
        with cls._cache_lock:
            if cls._cache_is_fresh() and cls._cached_header is not None:
                return cls._cached_header
        text = cls._load_text()
        return cls._store_cache(text)

    @classmethod
    def set_text(cls, value: str) -> None:
        with AppSettingsRepository() as app_settings_repo:
            app_settings_repo.set_value(
                key=cls.key,
                value=value
            )
            app_settings_repo.session.commit()
        cls.invalidate_cache()
