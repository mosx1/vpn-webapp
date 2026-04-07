from abc import ABC, abstractmethod
from db.models import User


class UserControlBase(ABC):
    
    def __init__(self, user: User) -> None:
        self.user = user

    @abstractmethod
    def delete(self, user_ids: set, server_id: int) -> None: ...
    @abstractmethod
    def add(self, user_id: int, server_id: int) -> str | None: ...