from ..common import BaseRepository

from db.models import ServersTable, User

from sqlalchemy import select, func, text, and_

from typing import Any

from config_loader import read_config




class ServersRepository(BaseRepository[ServersTable]):
    
    def __init__(self):
        super().__init__(ServersTable)

    def get_very_free_server(self, country: Any | None = None, exclude_server_id: int | None = None) -> int:
        """
            Возвращает менее загруженный сервер по стране
            Если страна не передана - ищет по всем странам
        """
        # check_answers_servers()

        conf = read_config()

        query = (
            select(
                (func.count() / conf['BaseConfig'].getfloat('coefficient_load_servers') / ServersTable.speed).label('count'),
                ServersTable.id
            )
            .select_from(ServersTable)
            .join(
                User,
                and_(
                    User.server_id == ServersTable.id,
                    User.action == True
                ), 
                isouter=True
            )
        )
        
        if country:
            query = query.filter(ServersTable.country == country.value)

        if exclude_server_id:
            query = query.filter(ServersTable.id != exclude_server_id)

        query = (
            query
            .group_by(ServersTable.id)
            .order_by(text('count ASC'))
            .limit(1)
        )
        result = self.session.execute(query).one()
        
        return result.id

    def get_info_all_servers(self):
        """
            Информация по всем серверам вместе
        """
        query = select(
            func.count().label("count"),
            func.count().filter(User.paid == True).label("count_pay")
        ).filter(User.action == True)
            
        return self.session.execute(query).one()

    def get_info_servers(self):
        """
            Информация отдельно по каждому серверу
        """
        conf = read_config()
        query = (
            select(
                ServersTable.name.label("name"),
                ServersTable.answers,
                func.count().label("count"),
                func.count().filter(User.paid == True).label("count_pay"),
                (func.count() / conf['BaseConfig'].getfloat('coefficient_load_servers') / ServersTable.speed * 100).label('load')
            ).join(
                User, ServersTable.id == User.server_id
            ).filter(
                User.action == True
            ).group_by(
                ServersTable.name,
                ServersTable.speed,
                ServersTable.answers
            )
        ).order_by(text('count_pay DESC'))
            
        return self.session.execute(query).all()