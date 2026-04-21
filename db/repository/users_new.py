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
        query = select(UserNew.id).order_by(UserNew.id.desc()).limit(1)
        result = self.session.execute(query)
        return (result.scalar_one() + 1) * -1