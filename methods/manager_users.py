from db.repository.users import UsersRepository
from db.models import User
from db.enums import Protocols
from methods.controller_manager_xray_api import UserControlXray
from methods.interfaces import UserControlBase

from abc import ABC, abstractmethod





class UserControlFactory:
    _protocols = {
        Protocols.xray.value: UserControlXray
        # Protocols.amneziawg.value: UserControlAmneziaWG
    }
    @classmethod
    def get_methods_for_protocol(self, user: User) -> UserControlBase:
        self.user = user
        return self._protocols[self.user.protocol]


class UserControl:

    def __init__(self, telegram_id: int) -> None:
        with UsersRepository() as users_repo:
            self.user: User = users_repo.get_by_id(telegram_id)
        self.protocol_methods = UserControlFactory.get_methods_for_protocol(self.user)

    def delete(self) -> None:
        with UsersRepository() as users_repo:
            users_repo.update(self.user.telegram_id, {"action": False})
            users_repo.session.commit()
        self.protocol_methods.delete(set([self.user.telegram_id]), self.user.server_id)
    
    def add(self, server_id: int) -> None:
        link = self.protocol_methods.add(self.user.telegram_id, server_id)
        with UsersRepository() as users_repo:
            users_repo.update(
                self.user.telegram_id, 
                {
                    "server_link": link,
                    "action": True
                }
            )
            users_repo.session.commit()
        