import jwt

from typing import Any

from flask import request
from db.repository.users import UsersRepository
from db.repository.security import SecurityRepository
from db.models import User
from db.enums import Protocols
from methods.controller_manager_xray_api import UserControlXray
from methods.controller_amneziawg import UserControlAmneziaWG
from methods.interfaces import UserControlBase

from config_loader import read_config


class UserControlFactory:
    _protocols = {
        Protocols.xray.value: UserControlXray,
        Protocols.amneziawg.value: UserControlAmneziaWG
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
        self.__init__(self.user.telegram_id)
    
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
        self.__init__(self.user.telegram_id)
    
    def update_protocol(self, protocol: Protocols) -> None:
        self.protocol_methods.delete(set([self.user.telegram_id]), self.user.server_id)
        with UsersRepository() as user_repo:
            user_repo.update(
                self.user.telegram_id,
                {
                    "protocol": protocol.value
                }
            )
            user_repo.session.commit()
            user: User = user_repo.get_by_id(self.user.telegram_id)
            self.protocol_methods = UserControlFactory.get_methods_for_protocol(user)
            link = self.protocol_methods.add(user.telegram_id, user.server_id)

            user_repo.update(
                user.telegram_id,
                {
                    "server_link": link
                }
            )
            user_repo.session.commit()
        self.__init__(user.telegram_id)


def get_current_user() -> User | None:

    config = read_config()

    raw_jwt = request.args.get('token').strip()

    with SecurityRepository() as security_rep:
        data_from_jwt: dict[str, Any] = jwt.decode(
            raw_jwt,
            security_rep.get(), 
            algorithms=config['JWT'].get('algoritm')
        )
    with UsersRepository() as user_rep:
        return user_rep.get_by_telegram_id(data_from_jwt['telegram_id'])