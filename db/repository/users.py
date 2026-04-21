from ..common import BaseRepository

from db.models import User, ServersTable, UserNew

from typing import Iterable, Any

from sqlalchemy import select, update, insert, text

from connect import config



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
    
    def create_user_by_email(
        self, 
        email: str, 
        telegram_id: int,
        server_link: str,
        server_id: int
    ) -> None:
        """Создание записи"""
        
        stmt2 = (
            insert(User).values(
                telegram_id=str(telegram_id),
                exit_date=text(f"now() + interval '{config['BaseConfig'].getint('tree_days')} days'"),
                action=True,
                server_link=server_link,
                server_id=str(server_id),
                protocol=config['BaseConfig'].getint('default_protocol')
            )
        )
        self.session.execute(stmt2)
        stmt = (
            insert(UserNew)
            .values(
                email=email,
                telegram_id=telegram_id
            )
        )
        self.session.execute(stmt)
        return