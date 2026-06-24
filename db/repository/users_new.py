from ..common import BaseRepository

from db.models import UserNew

from sqlalchemy import select


class UsersNewRepository(BaseRepository[UserNew]):

    def __init__(self) -> None:
        super().__init__(UserNew)
    
    def get_next_id_user(self) -> int:
        """
            Возвращает следующий доступный id юзера
        """
        query = select(UserNew.telegram_id).order_by(UserNew.telegram_id.asc()).limit(1)
        result = self.session.execute(query)
        r = result.scalar_one()
        if r > 0:
            r = r * -1
        return (r - 1)

    def get_by_id(self, telegram_id: int) -> UserNew | None:
        """
            Возвращает юзера по ид
        """
        query = select(UserNew).filter(UserNew.telegram_id == telegram_id)
        result = self.session.execute(query)
        return result.scalar_one_or_none()