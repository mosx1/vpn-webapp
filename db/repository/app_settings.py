from sqlalchemy import select

from ..common import BaseRepository
from db.models import AppSetting


class AppSettingsRepository(BaseRepository[AppSetting]):

    def __init__(self) -> None:
        super().__init__(AppSetting)

    def set_value(self, key: str, value: str) -> None:
        setting = self.get_by_id(key)
        if setting:
            setting.value = value
            return
        self.create(
            AppSetting(
                key=key,
                value=value
            )
        )
