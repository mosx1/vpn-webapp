from ..common import BaseRepository

from db.models import SecurityHashs

from sqlalchemy import select


class SecurityRepository(BaseRepository[SecurityHashs]):
    
    def __init__(self):
        super().__init__(SecurityHashs)

    def get(self) -> str:

        query = select(SecurityHashs).limit(1)
        hash_code: SecurityHashs | None = self.session.execute(query).scalar()

        if hash_code:
            return hash_code.hash