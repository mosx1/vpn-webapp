from sqlalchemy.orm import query
from ..common import BaseRepository

from db.models import ServersTable, User

from sqlalchemy import select, func, text, and_

from configparser import ConfigParser

from typing import Any




class ServersRepository(BaseRepository[ServersTable]):
    
    def __init__(self):
        super().__init__(ServersTable)

    def get_very_free_server(self, country: Any | None = None, exclude_server_id: int | None = None) -> int:
        """
            Возвращает менее загруженный сервер по стране
            Если страна не передана - ищет по всем странам
        """
        # check_answers_servers()

        conf = ConfigParser()
        conf.read('config.ini')

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
            .filter(
                ServersTable.answers == True
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