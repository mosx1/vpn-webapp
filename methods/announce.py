import base64

from db.repository.app_settings import AppSettingsRepository
from db.models import AppSetting
from methods.interfaces import AppSettingsBase


class Annonce(AppSettingsBase):

    key: str = "subscription_announce_text"
    DEFAULT_SUBSCRIPTION_ANNOUNCE_TEXT = (
        "Личный кабинет переехал на сайт kuzmos.ru.\n"
    )

    @classmethod
    def get_text(cls) -> str:
        with AppSettingsRepository() as app_settings_repo:
            announce_text = app_settings_repo.get_one(AppSetting.key == cls.key)
        if not announce_text:
            return cls.DEFAULT_SUBSCRIPTION_ANNOUNCE_TEXT
        return announce_text.value

    @classmethod
    def get_header_value(cls) -> str:
        announce_text = cls.get_text()
        encoded_announce = base64.b64encode(announce_text.encode("utf-8")).decode("ascii")
        return f"base64:{encoded_announce}"

    @classmethod
    def set_text(cls, value: str) -> None:
        with AppSettingsRepository() as app_settings_repo:
            app_settings_repo.set_value(
                key=cls.key,
                value=value
            )
            app_settings_repo.session.commit()
