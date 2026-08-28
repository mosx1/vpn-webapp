import jwt
import json

from typing import Any

from flask import request

from db.repository.users import UsersRepository
from db.repository.security import SecurityRepository
from db.repository.servers import ServersRepository
from db.repository.users_new import UsersNewRepository
from db.models import ServersTable, User
from db.enums import Protocols, PanelXray

from methods.controller_manager_xray_api import UserControlXray
from methods.controller_amneziawg import UserControlAmneziaWG
from methods.controller_3x_ui import UserControl3xUI
from methods.interfaces import UserControlBase
from connect import logging

from config_loader import read_config

from sqlalchemy import text
from datetime import datetime


class UserControlFactory:
    _protocols = {
        Protocols.xray.value: [UserControlXray, UserControl3xUI],
        Protocols.amneziawg.value: [UserControlAmneziaWG]
    }

    @classmethod
    def get_methods_for_user_on_server(cls, user: User, server_id: int) -> UserControlBase:
        with ServersRepository() as servers_repo:
            server: ServersTable | None = servers_repo.get_by_id(server_id)
        if not server:
            raise ValueError(f"Server with id={server_id} not found")
        match user.protocol:
            case Protocols.amneziawg.value:
                return UserControlAmneziaWG(user)
            case Protocols.xray.value:
                match server.panel_xray:
                    case PanelXray.xray.value:
                        return UserControlXray(user)
                    case PanelXray.xui.value:
                        return UserControl3xUI(user)
                    case _:
                        raise ValueError(f"Invalid panel xray: {server.panel_xray}")
            case _:
                raise ValueError(f"Invalid protocol: {user.protocol}")

    @classmethod
    def get_methods_for_protocol(cls, user: User) -> UserControlBase:
        return cls.get_methods_for_user_on_server(user, user.server_id)


class UserControl:

    def __init__(self, telegram_id: int) -> None:
        with UsersRepository() as users_repo:
            self.user: User = users_repo.get_by_id(telegram_id)
        self.protocol_methods = UserControlFactory.get_methods_for_protocol(self.user)

    def delete(self) -> None:
        current_user_id = int(self.user.telegram_id)
        current_server_id = int(self.user.server_id)
        with UsersRepository() as users_repo:
            users_repo.update(current_user_id, {"action": False})
            users_repo.session.commit()
        self.protocol_methods.delete(set([current_user_id]), current_server_id)
        self.__init__(current_user_id)
    
    def add(self, server_id: int) -> None:
        current_user_id = int(self.user.telegram_id)
        link = self.protocol_methods.add(current_user_id, server_id)
        with UsersRepository() as users_repo:
            users_repo.update(
                current_user_id,
                {
                    "server_link": link,
                    "action": True
                }
            )
            users_repo.session.commit()
        self.__init__(current_user_id)
    
    def update_protocol(self, protocol: Protocols) -> None:
        current_user_id = int(self.user.telegram_id)
        current_server_id = int(self.user.server_id)
        self.protocol_methods.delete(set([current_user_id]), current_server_id)
        with UsersRepository() as user_repo:
            user_repo.update(
                current_user_id,
                {
                    "protocol": protocol.value
                }
            )
            user_repo.session.commit()
            user: User = user_repo.get_by_id(current_user_id)
            self.protocol_methods = UserControlFactory.get_methods_for_protocol(user)
            link = self.protocol_methods.add(user.telegram_id, user.server_id)

            user_repo.update(
                user.telegram_id,
                {
                    "server_link": link
                }
            )
            user_repo.session.commit()
        self.__init__(current_user_id)

    def update_server(self, server_id: int) -> None:
        current_user_id = int(self.user.telegram_id)
        current_server_id = int(self.user.server_id)

        if server_id == current_server_id:
            return

        new_protocol_methods = UserControlFactory.get_methods_for_user_on_server(
            self.user,
            server_id
        )
        link = new_protocol_methods.add(current_user_id, server_id)
        if isinstance(link, dict):
            link = json.dumps(link)
        if not link:
            raise RuntimeError(
                f"Failed to obtain subscription link on server {server_id} for user {current_user_id}"
            )

        old_protocol_methods = self.protocol_methods
        try:
            old_protocol_methods.delete(set([current_user_id]), current_server_id)
        except Exception as error:
            logging.warning(
                "Skip delete on old server %s for user %s: %s",
                current_server_id,
                current_user_id,
                error
            )

        try:
            with UsersRepository() as users_repo:
                users_repo.update(
                    current_user_id,
                    {
                        "server_id": server_id,
                        "server_link": link,
                    }
                )
                users_repo.session.commit()
        except Exception:
            try:
                new_protocol_methods.delete(set([current_user_id]), server_id)
            except Exception as cleanup_error:
                logging.warning(
                    "Failed to rollback user %s on server %s after DB error: %s",
                    current_user_id,
                    server_id,
                    cleanup_error,
                )
            raise

        self.__init__(current_user_id)
    
    @staticmethod
    def create(email: str) -> None:
        with ServersRepository() as servers_repo:
            server_id: int = servers_repo.get_very_free_server()
            server: ServersTable = servers_repo.get_by_id(server_id)
        with UsersNewRepository() as users_new_repo:
            users_new_id = users_new_repo.get_next_id_user()
        match server.panel_xray:
            case PanelXray.xray.value:
                strategy = UserControlXray
            case PanelXray.xui.value:
                strategy = UserControl3xUI
            case _:
                raise ValueError(f"Invalid panel xray: {server.panel_xray}")
        server_link = strategy.add(users_new_id, server_id)
        with UsersRepository() as users_repo:
            users_repo.create_user_by_email(
                email=email,
                telegram_id=users_new_id,
                server_link=server_link,
                server_id=server_id
            )
            
            users_repo.session.commit()
        return users_new_id
    
    def prolongation(self, day: int) -> None:
        with UsersRepository() as users_repo:
            user: User = users_repo.get_by_telegram_id(self.user.telegram_id)
            new_exit_date = text(f"exit_date + interval '{day} days'")
            if user.exit_date < datetime.now():
                new_exit_date =text(f"now() + interval '{day} days'")

            users_repo.update(
                self.user.telegram_id,
                {
                    "exit_date": new_exit_date,
                    "action": True,
                    "paid": True
                }
            )
            users_repo.session.commit()

    def reduce_subscription(self, day: int) -> None:
        with UsersRepository() as users_repo:
            users_repo.update(
                self.user.telegram_id,
                {
                    "exit_date": text(f"exit_date - interval '{day} days'")
                }
            )
            users_repo.session.commit()

    def add_referal(user_id: int, referal: int) -> None:
        with UsersRepository() as users_repo:
            users_repo.update(
                user_id,
                {
                    "invited": referal
                }
            )
            user_control = UserControl(referal)
            user_control.prolongation(30)
            users_repo.session.commit()


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


def get_link_subscription(telegram_id: str | int) -> str:
    """
        Отдает ссылку для получения подписки
    """
    config = read_config()

    with SecurityRepository() as security_rep:
        token: str = jwt.encode(
            {"telegram_id": telegram_id},
            security_rep.get(), 
            algorithm=config['JWT'].get('algoritm')
        )

        return f"https://kuzmos.ru/sub?jwt={token}"