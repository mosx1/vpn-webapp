"""Две строки user_to_subscription для xray_api и сборка подписки."""

import json
from contextlib import contextmanager
from types import SimpleNamespace

from db.enums import PanelXray, Protocols
from methods import manager_users
from methods.manager_users import UserControl
from methods.xray_subscription import build_subscription_payload, merge_xray_client_configs


def _proxy_config(address: str, tag: str = "proxy") -> dict:
    return {
        "outbounds": [
            {
                "tag": tag,
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": address,
                            "port": 443,
                            "users": [{"id": "uuid", "flow": "xtls-rprx-vision"}],
                        }
                    ]
                },
                "streamSettings": {
                    "realitySettings": {
                        "serverName": "example.com",
                        "publicKey": "pk",
                        "shortId": "sid",
                    }
                },
            },
            {"tag": "direct", "protocol": "freedom"},
        ],
        "routing": {
            "rules": [
                {"type": "field", "outboundTag": "proxy", "network": "tcp,udp"}
            ]
        },
    }


def test_single_subscription_keeps_original_link():
    payload = build_subscription_payload([(1, "vless://one")])
    assert payload == "vless://one"


def test_two_json_configs_merge_into_balancer():
    first = json.dumps(_proxy_config("1.1.1.1"))
    second = json.dumps(_proxy_config("2.2.2.2"))

    payload = json.loads(build_subscription_payload([(10, first), (20, second)]))

    proxy_tags = [outbound["tag"] for outbound in payload["outbounds"] if outbound["protocol"] == "vless"]
    assert proxy_tags == ["proxy-10", "proxy-20"]
    assert payload["routing"]["balancers"][0]["strategy"]["type"] == "leastPing"
    assert payload["routing"]["rules"][0]["balancerTag"] == "balancer"
    assert "outboundTag" not in payload["routing"]["rules"][0]
    assert payload["observatory"]["subjectSelector"] == ["proxy-"]


def test_merge_keeps_direct_outbound_from_first_config():
    merged = merge_xray_client_configs(
        [
            (1, _proxy_config("10.0.0.1")),
            (2, _proxy_config("10.0.0.2")),
        ]
    )
    tags = [outbound["tag"] for outbound in merged["outbounds"]]
    assert tags == ["proxy-1", "proxy-2", "direct"]


@contextmanager
def _fake_repo(repo):
    yield repo


def test_xray_add_writes_two_subscription_rows(monkeypatch):
    state = {
        "user": SimpleNamespace(
            telegram_id=7,
            server_id=1,
            protocol=Protocols.xray.value,
            action=True,
        ),
        "subscriptions": [
            SimpleNamespace(telegram_id=7, server_id=1, protocol=Protocols.xray.value)
        ],
        "servers": {
            1: SimpleNamespace(id=1, panel_xray=PanelXray.xray.value, answers=True),
            2: SimpleNamespace(id=2, panel_xray=PanelXray.xray.value, answers=True),
        },
        "updates": [],
        "replaces": [],
        "calls": [],
    }

    class FakeXray(manager_users.UserControlXray):
        def add(self, user_id, server_id):
            state["calls"].append(("add", server_id))
            return f'{{"outbounds":[{{"protocol":"vless","tag":"proxy"}}]}}'

        def delete(self, user_ids, server_id):
            state["calls"].append(("delete", server_id))

    servers_repo = SimpleNamespace(
        get_by_id=lambda server_id: state["servers"].get(server_id),
        get_servers_by_load=lambda **kwargs: [2],
    )
    users_repo = SimpleNamespace(
        get_by_telegram_id=lambda telegram_id: state["user"],
        update=lambda telegram_id, values: state["updates"].append((telegram_id, values)),
        session=SimpleNamespace(commit=lambda: None),
    )
    uts_repo = SimpleNamespace(
        get_by_telegram_id=lambda telegram_id: state["subscriptions"],
        replace_for_telegram_id=lambda telegram_id, server_links: state["replaces"].append(
            (telegram_id, server_links)
        ),
        session=SimpleNamespace(commit=lambda: None),
    )

    monkeypatch.setattr(manager_users, "ServersRepository", lambda: _fake_repo(servers_repo))
    monkeypatch.setattr(manager_users, "UsersRepository", lambda: _fake_repo(users_repo))
    monkeypatch.setattr(manager_users, "UserToSubscriptionRepository", lambda: _fake_repo(uts_repo))
    monkeypatch.setattr(
        manager_users.UserControlFactory,
        "get_methods_for_user_on_server",
        classmethod(lambda cls, user, server_id: FakeXray(user)),
    )
    monkeypatch.setattr(
        manager_users.UserControlFactory,
        "get_methods_for_protocol",
        classmethod(lambda cls, user: FakeXray(user)),
    )

    UserControl(7).add(1)

    assert ("add", 1) in state["calls"]
    assert ("add", 2) in state["calls"]
    assert state["updates"][0][0] == 7
    assert set(state["updates"][0][1]) >= {"server_id", "server_link", "action"}
    assert state["updates"][0][1]["action"] is True
    assert state["replaces"][0][0] == 7
    assert set(state["replaces"][0][1]) == {1, 2}


def test_delete_removes_user_from_both_servers(monkeypatch):
    state = {
        "user": SimpleNamespace(telegram_id=7, server_id=1, protocol=Protocols.xray.value),
        "subscriptions": [
            SimpleNamespace(telegram_id=7, server_id=1),
            SimpleNamespace(telegram_id=7, server_id=2),
        ],
        "updates": [],
        "calls": [],
        "servers": {
            1: SimpleNamespace(id=1, panel_xray=PanelXray.xray.value, answers=True),
            2: SimpleNamespace(id=2, panel_xray=PanelXray.xray.value, answers=True),
        },
    }

    class FakeXray(manager_users.UserControlXray):
        def delete(self, user_ids, server_id):
            state["calls"].append(("delete", server_id))

        def add(self, user_id, server_id):
            return "link"

    users_repo = SimpleNamespace(
        get_by_telegram_id=lambda telegram_id: state["user"],
        update=lambda user_id, values: state["updates"].append((user_id, values)),
        session=SimpleNamespace(commit=lambda: None),
    )
    servers_repo = SimpleNamespace(
        get_by_id=lambda server_id: state["servers"].get(server_id),
    )
    uts_repo = SimpleNamespace(
        get_by_telegram_id=lambda telegram_id: state["subscriptions"],
        session=SimpleNamespace(commit=lambda: None),
    )

    monkeypatch.setattr(manager_users, "UsersRepository", lambda: _fake_repo(users_repo))
    monkeypatch.setattr(manager_users, "ServersRepository", lambda: _fake_repo(servers_repo))
    monkeypatch.setattr(manager_users, "UserToSubscriptionRepository", lambda: _fake_repo(uts_repo))
    monkeypatch.setattr(
        manager_users.UserControlFactory,
        "get_methods_for_user_on_server",
        classmethod(lambda cls, user, server_id: FakeXray(user)),
    )
    monkeypatch.setattr(
        manager_users.UserControlFactory,
        "get_methods_for_protocol",
        classmethod(lambda cls, user: FakeXray(user)),
    )

    UserControl(7).delete()

    assert state["updates"] == [(7, {"action": False})]
    assert ("delete", 1) in state["calls"]
    assert ("delete", 2) in state["calls"]
