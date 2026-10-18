import jwt
import json
import copy

from typing import Any

from flask import request

from db.repository.users import UsersRepository
from db.repository.security import SecurityRepository
from db.repository.servers import ServersRepository
from db.repository.users_new import UsersNewRepository
from db.repository.user_to_subscription import UserToSubscriptionRepository
from db.models import ServersTable, User, UserToSubscription
from db.enums import Protocols, PanelXray

from methods.controller_manager_xray_api import UserControlXray
from methods.controller_amneziawg import UserControlAmneziaWG
from methods.controller_3x_ui import UserControl3xUI
from methods.interfaces import UserControlBase
from connect import logging

from config_loader import read_config

from sqlalchemy import text, and_
from datetime import datetime
from time import monotonic


TRANSFER_TIME_BUDGET_SECONDS = 60.0
_PROXY_PROTOCOLS = {"vless", "vmess", "trojan", "shadowsocks"}
_BALANCER_TAG = "balancer"
_PROXY_TAG_PREFIX = "proxy-"

class ServerProvisioningError(Exception):
    """Не удалось создать пользователя на целевом сервере."""


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


def _normalize_server_link(link: Any) -> str:
    if isinstance(link, dict):
        return json.dumps(link, ensure_ascii=False)
    return str(link) if link is not None else ""


def _sync_user_to_subscriptions(
    telegram_id: int,
    server_links: dict[int, str],
    email: str | None = None
) -> None:
    if email:
        with UsersNewRepository() as users_new_repo:
            users_new_repo.get_or_create(telegram_id, email)
            users_new_repo.session.commit()
    with UserToSubscriptionRepository() as uts_repo:
        uts_repo.replace_for_telegram_id(telegram_id, server_links)
        uts_repo.session.commit()


class UserControl:

    def __init__(self, telegram_id: int) -> None:
        with UsersRepository() as users_repo:
            self.user: User = users_repo.get_by_telegram_id(telegram_id)
        with UserToSubscriptionRepository() as uts_repo:
            self.server_subscriptions: list[UserToSubscription] = uts_repo.get_by_telegram_id(
                telegram_id
            )
        self.protocol_methods = UserControlFactory.get_methods_for_protocol(self.user)

    def _subscription_server_ids(self) -> list[int]:
        rows = getattr(self, "server_subscriptions", None) or []
        if rows:
            return [int(row.server_id) for row in rows]
        return [int(self.user.server_id)]

    def _delete_from_server(self, user_id: int, server_id: int, protocol_methods: UserControlBase | None = None) -> None:
        methods = protocol_methods or UserControlFactory.get_methods_for_user_on_server(self.user, server_id)
        methods.delete(set([user_id]), server_id)

    def _pick_xray_server_ids(self, preferred_server_id: int, exclude_server_ids: set[int] | None = None) -> list[int]:
        exclude_ids = set(exclude_server_ids or [])
        with ServersRepository() as servers_repo:
            preferred = servers_repo.get_by_id(preferred_server_id)
            preferred_ok = bool(
                preferred
                and preferred.panel_xray == PanelXray.xray.value
                and preferred.answers
            )
            extra_exclude = set(exclude_ids)
            if preferred_ok:
                extra_exclude.add(int(preferred_server_id))
            other_ids = servers_repo.get_servers_by_load(
                panel_xray=PanelXray.xray.value,
                exclude_server_ids=extra_exclude,
                limit=1 if preferred_ok else None
            )
        if preferred_ok:
            return [int(preferred_server_id), *other_ids]
        return other_ids

    def _provision_xray_servers(self, user_id: int, server_ids: list[int]) -> dict[int, str]:
        server_links: dict[int, str] = {}
        for target_server_id in server_ids:
            try:
                _methods, link = self._add_on_server(target_server_id)
            except ServerProvisioningError as error:
                logging.warning(
                    "Skip xray server %s for user %s: %s",
                    target_server_id,
                    user_id,
                    error
                )
                continue
            server_links[int(target_server_id)] = _normalize_server_link(link)
        if not server_links:
            raise ServerProvisioningError(
                f"Failed to add user {user_id} on xray servers {server_ids}"
            )
        return server_links

    def _persist_primary_and_subscriptions(
        self,
        telegram_id: int,
        server_links: dict[int, str],
        extra_values: dict | None = None
    ) -> None:
        extra_values = extra_values or {}
        primary_server_id = next(iter(server_links))
        with UserToSubscriptionRepository() as uts_repo:
            uts_repo.replace_for_telegram_id(telegram_id, server_links)
            uts_repo.session.commit()
        with UsersRepository() as users_repo:
            users_repo.update(
                telegram_id,
                {
                    "server_id": primary_server_id,
                    "server_link": merge_xray_client_configs(server_links),
                    **extra_values
                }
            )
            users_repo.session.commit()
        _sync_user_to_subscriptions(telegram_id, server_links)

    def delete(self) -> None:
        current_user_id = int(self.user.telegram_id)
        with UsersRepository() as users_repo:
            users_repo.update(current_user_id, {"action": False})
            users_repo.session.commit()
        for server_id in self._subscription_server_ids():
            try:
                self._delete_from_server(current_user_id, server_id)
            except Exception as error:
                logging.warning(
                    "Skip delete on server %s for user %s: %s",
                    server_id,
                    current_user_id,
                    error
                )
        self.__init__(current_user_id)
    
    def add(self, server_id: int) -> None:
        current_user_id = int(self.user.telegram_id)
        protocol_methods = UserControlFactory.get_methods_for_user_on_server(self.user, server_id)
        if isinstance(protocol_methods, UserControlXray):
            with ServersRepository() as servers_repo:
                servers = servers_repo.get_server_list(
                    and_(
                        ServersTable.panel_xray==PanelXray.xray.value,
                        ServersTable.answers==True
                    )
                )
                server_ids = [server.id for server in servers]
                server_links = self._provision_xray_servers(current_user_id, server_ids)
                self._persist_primary_and_subscriptions(
                    current_user_id,
                    server_links,
                    {"action": True}
                )
                self.__init__(current_user_id)
                return

        link = protocol_methods.add(current_user_id, server_id)
        normalized_link = _normalize_server_link(link)
        with UsersRepository() as users_repo:
            users_repo.update(
                current_user_id,
                {
                    "server_link": normalized_link,
                    "action": True
                }
            )
            users_repo.session.commit()
        _sync_user_to_subscriptions(
            current_user_id,
            {int(server_id): normalized_link}
        )
        self.__init__(current_user_id)
    
    def update_protocol(self, protocol: Protocols) -> None:
        current_user_id = int(self.user.telegram_id)
        current_server_id = int(self.user.server_id)
        for server_id in self._subscription_server_ids():
            try:
                self._delete_from_server(current_user_id, server_id)
            except Exception as error:
                logging.warning(
                    "Skip delete on server %s while changing protocol for user %s: %s",
                    server_id,
                    current_user_id,
                    error
                )
        with UsersRepository() as user_repo:
            user_repo.update(
                current_user_id,
                {
                    "protocol": protocol.value
                }
            )
            user_repo.session.commit()
        self.__init__(current_user_id)
        self.add(current_server_id)

    def _add_on_server(self, server_id: int) -> tuple[UserControlBase, str]:
        """
            Создает пользователя на указанном сервере и возвращает методы протокола со ссылкой

            @throws ServerProvisioningError Если сервер недоступен или не отдал ссылку
        """
        current_user_id = int(self.user.telegram_id)
        try:
            protocol_methods = UserControlFactory.get_methods_for_user_on_server(
                self.user,
                server_id
            )
            link = protocol_methods.add(current_user_id, server_id)
        except Exception as error:
            raise ServerProvisioningError(
                f"Failed to add user {current_user_id} on server {server_id}: {error}"
            ) from error

        if isinstance(link, dict):
            link = json.dumps(link)
        if not link:
            raise ServerProvisioningError(
                f"Failed to obtain subscription link on server {server_id} for user {current_user_id}"
            )

        return protocol_methods, link

    @staticmethod
    def _is_server_unreachable(server_id: int) -> bool:
        """
            Проверяет, помечена ли нода как недоступная

            Поле answers заполняет health-check по эндпоинту xray-api /config,
            поэтому оно отражает доступность только для панели xray.
            Для остальных панелей answers не показателен и доступность не проверяется
        """
        with ServersRepository() as servers_repo:
            server: ServersTable | None = servers_repo.get_by_id(server_id)

        if not server:
            return True
        if server.panel_xray != PanelXray.xray.value:
            return False

        return not server.answers

    def transfer_to_free_server(
        self,
        country: Any | None = None,
        time_budget: float = TRANSFER_TIME_BUDGET_SECONDS
    ) -> int:
        """
            Переносит пользователя на менее загруженный доступный сервер

            Если добавление на сервер не удалось - пробует следующий по загруженности.
            Перебор ограничен по времени, чтобы запрос не был убит по таймауту gunicorn

            @throws ServerProvisioningError Если ни один из серверов не принял пользователя
        """
        self.add(self.user.server_id)
        return self.user.server_id
        current_user_id = int(self.user.telegram_id)
        current_server_id = int(self.user.server_id)
        current_server_ids = self._subscription_server_ids()

        with ServersRepository() as servers_repo:
            candidate_server_ids = servers_repo.get_servers_by_load(
                country=country,
                exclude_server_id=current_server_id,
                exclude_server_ids=current_server_ids
            )

        if not candidate_server_ids:
            raise ServerProvisioningError(
                f"No available servers to transfer user {current_user_id} from server {current_server_id}"
            )

        started_at = monotonic()
        attempted_server_ids: list[int] = []

        for candidate_server_id in candidate_server_ids:
            if attempted_server_ids and monotonic() - started_at > time_budget:
                logging.warning(
                    "Transfer of user %s stopped by time budget after servers %s",
                    current_user_id,
                    attempted_server_ids
                )
                break

            attempted_server_ids.append(candidate_server_id)
            try:
                self.update_server(candidate_server_id)
                return candidate_server_id
            except ServerProvisioningError as error:
                logging.warning(
                    "Transfer of user %s to server %s failed, trying next server: %s",
                    current_user_id,
                    candidate_server_id,
                    error
                )

        raise ServerProvisioningError(
            f"Failed to transfer user {current_user_id} to any of servers {attempted_server_ids}"
        )

    def update_server(self, server_id: int) -> None:
        current_user_id = int(self.user.telegram_id)
        current_server_ids = self._subscription_server_ids()
        current_server_id = int(self.user.server_id)

        if server_id in current_server_ids:
            return

        new_protocol_methods, link = self._add_on_server(server_id)
        server_links = {int(server_id): _normalize_server_link(link)}

        if isinstance(new_protocol_methods, UserControlXray):
            extra_ids = self._pick_xray_server_ids(
                server_id,
                exclude_server_ids=set(current_server_ids)
            )
            for extra_server_id in extra_ids:
                if extra_server_id == int(server_id):
                    continue
                try:
                    _methods, extra_link = self._add_on_server(extra_server_id)
                    server_links[int(extra_server_id)] = _normalize_server_link(extra_link)
                except ServerProvisioningError as error:
                    logging.warning(
                        "Skip extra xray server %s while transferring user %s: %s",
                        extra_server_id,
                        current_user_id,
                        error
                    )

        for old_server_id in current_server_ids:
            if old_server_id in server_links:
                continue
            if self._is_server_unreachable(old_server_id):
                logging.warning(
                    "Old server %s is unreachable, skip delete for user %s "
                    "(stale client will be removed by foreign users cleanup)",
                    old_server_id,
                    current_user_id
                )
                continue
            try:
                old_methods = (
                    self.protocol_methods
                    if old_server_id == current_server_id
                    else None
                )
                self._delete_from_server(current_user_id, old_server_id, old_methods)
            except Exception as error:
                logging.warning(
                    "Skip delete on old server %s for user %s: %s",
                    old_server_id,
                    current_user_id,
                    error
                )

        try:
            self._persist_primary_and_subscriptions(current_user_id, server_links)
        except Exception:
            for provisioned_server_id in server_links:
                try:
                    new_protocol_methods.delete(set([current_user_id]), provisioned_server_id)
                except Exception as cleanup_error:
                    logging.warning(
                        "Failed to rollback user %s on server %s after DB error: %s",
                        current_user_id,
                        provisioned_server_id,
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

        if server.panel_xray == PanelXray.xray.value:
            with ServersRepository() as servers_repo:
                target_server_ids = servers_repo.get_servers_by_load(
                    panel_xray=PanelXray.xray.value,
                    limit=2
                )
            if not target_server_ids:
                target_server_ids = [server_id]
            server_links: dict[int, str] = {}
            for target_server_id in target_server_ids:
                link = strategy.add(users_new_id, target_server_id)
                if not link:
                    logging.warning(
                        "Failed to add new user %s on xray server %s",
                        users_new_id,
                        target_server_id
                    )
                    continue
                server_links[int(target_server_id)] = _normalize_server_link(link)
            if not server_links:
                raise ServerProvisioningError(
                    f"Failed to add new user {users_new_id} on xray servers {target_server_ids}"
                )
            primary_server_id = next(iter(server_links))
            with UsersRepository() as users_repo:
                users_repo.create_user_by_email(
                    email=email,
                    telegram_id=users_new_id,
                    server_link=server_links[primary_server_id],
                    server_id=primary_server_id
                )
                users_repo.session.commit()
            _sync_user_to_subscriptions(users_new_id, server_links, email=email)
            return users_new_id

        server_link = strategy.add(users_new_id, server_id)
        with UsersRepository() as users_repo:
            users_repo.create_user_by_email(
                email=email,
                telegram_id=users_new_id,
                server_link=server_link,
                server_id=server_id
            )
            
            users_repo.session.commit()
        _sync_user_to_subscriptions(
            users_new_id,
            {int(server_id): _normalize_server_link(server_link)},
            email=email
        )
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



def _is_proxy_outbound(outbound: dict) -> bool:
    protocol = str(outbound.get("protocol") or "").lower()
    tag = str(outbound.get("tag") or "")
    if protocol in _PROXY_PROTOCOLS:
        return True
    return tag == "proxy" or tag.startswith(_PROXY_TAG_PREFIX)

def _split_outbounds(config: dict) -> tuple[list[dict], list[dict]]:
    outbounds = list(config.get("outbounds") or [])
    proxies = [outbound for outbound in outbounds if _is_proxy_outbound(outbound)]
    others = [outbound for outbound in outbounds if not _is_proxy_outbound(outbound)]
    if not proxies and outbounds:
        return [outbounds[0]], outbounds[1:]
    return proxies, others


def merge_xray_client_configs(server_configs: list[tuple[int, dict]]) -> dict[str, Any]:
    """
        Собирает один клиентский JSON из конфигов нескольких серверов.

        Каждый proxy-outbound получает тег proxy-<server_id>, а маршрутизация
        идет через balancer xray-ядра (leastPing + observatory).
    """
    if not server_configs:
        raise ValueError("server_configs must not be empty")

    if len(server_configs) == 1:
        return copy.deepcopy(server_configs[0][1])

    base_server_id, base_config = server_configs[0]
    merged = copy.deepcopy(base_config)
    _base_proxies, base_others = _split_outbounds(merged)

    proxy_outbounds: list[dict] = []
    for server_id, config in server_configs:
        proxies, _others = _split_outbounds(config)
        if not proxies:
            continue
        proxy = copy.deepcopy(proxies[0])
        proxy["tag"] = f"{_PROXY_TAG_PREFIX}{int(server_id)}"
        proxy_outbounds.append(proxy)

    if not proxy_outbounds:
        return merged

    merged["outbounds"] = proxy_outbounds + copy.deepcopy(base_others)

    routing = merged.setdefault("routing", {})
    routing["balancers"] = [
        balancer
        for balancer in (routing.get("balancers") or [])
        if balancer.get("tag") != _BALANCER_TAG
    ]
    selector_tags = [outbound["tag"] for outbound in proxy_outbounds]
    routing["balancers"].append(
        {
            "tag": _BALANCER_TAG,
            "selector": [_PROXY_TAG_PREFIX],
            "fallbackTag": f"{_PROXY_TAG_PREFIX}{int(base_server_id)}",
            "strategy": {"type": "leastPing"},
        }
    )

    rules = list(routing.get("rules") or [])
    replaced_existing_rule = False
    for rule in rules:
        outbound_tag = rule.get("outboundTag")
        if outbound_tag in {"proxy", *selector_tags} or str(outbound_tag).startswith(_PROXY_TAG_PREFIX):
            rule.pop("outboundTag", None)
            rule["balancerTag"] = _BALANCER_TAG
            replaced_existing_rule = True
    if not replaced_existing_rule:
        rules.append(
            {
                "type": "field",
                "network": "tcp,udp",
                "balancerTag": _BALANCER_TAG,
            }
        )
    routing["rules"] = rules

    merged["observatory"] = {
        "subjectSelector": [_PROXY_TAG_PREFIX],
        "probeUrl": "https://www.gstatic.com/generate_204",
        "probeInterval": "2s",
        "enableConcurrency": True,
    }
    return merged