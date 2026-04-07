from ..common import BaseRepository

from db.models import User, ServersTable

from typing import Iterable, Any, Optional

from sqlalchemy import select, update



class UsersRepository(BaseRepository[User]):
    
    def __init__(self) -> None:
        super().__init__(User)

    def get_all(self, limit: int | None = None, offset: int | None = None) -> Iterable:
        """
            Получение всех записей с пагинацией и ссылкой на сервер
        """
        stmt = (
            select(
                User,
                ServersTable.links
            )
            .join(
                ServersTable,
                ServersTable.id == User.server_id
            )
        )

        if limit:
            stmt = stmt.limit(limit)
        if offset:
            stmt = stmt.offset(offset)

        result = self.session.execute(stmt)

        return result.fetchall()
    
    def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """
            Возвращает юзера по ид телеграмма
        """
        query = select(User).filter(User.telegram_id == telegram_id)
        result = self.session.execute(query)
        return result.scalar_one_or_none()
        
    
    def update(self, id: Any, update_data: dict) -> User | None:
        """Обновление записи"""
        stmt = (
            update(User)
            .where(User.telegram_id == id)
            .values(**update_data)
            .returning(User)
        )
        result = self.session.execute(stmt)  # noqa: F811
        return result.scalar_one_or_none()