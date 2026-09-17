"""Проверка перебора серверов при смене сервера пользователем."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from db.enums import PanelXray
from methods import manager_users
from methods.manager_users import ServerProvisioningError, UserControl


class FakePanel:
    """Панель, которая принимает пользователя только на разрешенных серверах."""

    def __init__(self, healthy_server_ids: set[int], calls: list):
        self._healthy_server_ids = healthy_server_ids
        self._calls = calls

    def add(self, user_id: int, server_id: int) -> str | None:
        self._calls.append(("add", server_id))
        if server_id not in self._healthy_server_ids:
            raise ConnectionError(f"server {server_id} unreachable")
        return f"vless://link-{server_id}"

    def delete(self, user_ids: set[int], server_id: int) -> None:
        self._calls.append(("delete", server_id))


@contextmanager
def _fake_repo(repo):
    yield repo


@pytest.fixture
def transfer_env(monkeypatch):
    """Подменяет БД и панели, возвращает управление сценарием переноса."""
    state = {
        "candidates": [],
        "healthy": set(),
        "calls": [],
        "updates": [],
        "user": SimpleNamespace(telegram_id=1, server_id=100, protocol=1),
        # Текущая нода пользователя: живой сервер на панели xray
        "servers": {
            100: SimpleNamespace(id=100, panel_xray=PanelXray.xray.value, answers=True)
        },
    }

    servers_repo = SimpleNamespace(
        get_servers_by_load=lambda country=None, exclude_server_id=None, limit=None: [
            server_id for server_id in state["candidates"] if server_id != exclude_server_id
        ],
        get_by_id=lambda server_id: state["servers"].get(server_id),
    )
    monkeypatch.setattr(manager_users, "ServersRepository", lambda: _fake_repo(servers_repo))

    def users_repo_factory():
        def update(user_id, values):
            state["updates"].append((user_id, values))

        return _fake_repo(
            SimpleNamespace(update=update, session=SimpleNamespace(commit=lambda: None))
        )

    monkeypatch.setattr(manager_users, "UsersRepository", users_repo_factory)
    monkeypatch.setattr(
        manager_users.UserControlFactory,
        "get_methods_for_user_on_server",
        classmethod(lambda cls, user, server_id: FakePanel(state["healthy"], state["calls"])),
    )

    def fake_init(self, telegram_id):
        self.user = state["user"]
        self.protocol_methods = FakePanel(state["healthy"], state["calls"])

    monkeypatch.setattr(UserControl, "__init__", fake_init)

    return state


def test_falls_back_to_next_server_by_load(transfer_env):
    """Первые два сервера недоступны - пользователь уезжает на третий."""
    transfer_env["candidates"] = [1, 2, 3, 4]
    transfer_env["healthy"] = {3, 4}

    chosen_server_id = UserControl(1).transfer_to_free_server()

    assert chosen_server_id == 3
    add_attempts = [server_id for action, server_id in transfer_env["calls"] if action == "add"]
    assert add_attempts == [1, 2, 3]
    assert transfer_env["updates"] == [(1, {"server_id": 3, "server_link": "vless://link-3"})]


def test_uses_first_server_when_it_is_available(transfer_env):
    """Если самый свободный сервер жив - других не трогаем."""
    transfer_env["candidates"] = [7, 8]
    transfer_env["healthy"] = {7, 8}

    assert UserControl(1).transfer_to_free_server() == 7
    assert [server_id for action, server_id in transfer_env["calls"] if action == "add"] == [7]


def test_raises_when_no_server_accepts_user(transfer_env):
    """Все серверы недоступны - переносить некуда, БД не меняем."""
    transfer_env["candidates"] = [1, 2]
    transfer_env["healthy"] = set()

    with pytest.raises(ServerProvisioningError):
        UserControl(1).transfer_to_free_server()

    assert transfer_env["updates"] == []


def test_current_server_is_excluded_from_candidates(transfer_env):
    """Текущий сервер пользователя не должен попадать в кандидаты."""
    transfer_env["candidates"] = [100, 5]
    transfer_env["healthy"] = {100, 5}

    assert UserControl(1).transfer_to_free_server() == 5


def test_deletes_from_old_server_when_it_is_alive(transfer_env):
    """Живая нода - отключаем подписку на ней как обычно."""
    transfer_env["candidates"] = [5]
    transfer_env["healthy"] = {5}

    UserControl(1).transfer_to_free_server()

    assert ("delete", 100) in transfer_env["calls"]


def test_skips_delete_when_old_server_is_unreachable(transfer_env):
    """answers=False на панели xray - удаление пропускаем, добавляем на новую."""
    transfer_env["candidates"] = [5]
    transfer_env["healthy"] = {5}
    transfer_env["servers"][100].answers = False

    assert UserControl(1).transfer_to_free_server() == 5

    assert ("delete", 100) not in transfer_env["calls"]
    assert ("add", 5) in transfer_env["calls"]
    assert transfer_env["updates"] == [(1, {"server_id": 5, "server_link": "vless://link-5"})]


def test_still_deletes_from_xui_server_with_false_answers(transfer_env):
    """Для панели 3x-ui answers не отражает доступность - удаление не пропускаем."""
    transfer_env["candidates"] = [5]
    transfer_env["healthy"] = {5}
    transfer_env["servers"][100].panel_xray = PanelXray.xui.value
    transfer_env["servers"][100].answers = False

    UserControl(1).transfer_to_free_server()

    assert ("delete", 100) in transfer_env["calls"]


def test_skips_delete_when_old_server_row_is_missing(transfer_env):
    """Сервер удален из справочника - удалять с него нечего."""
    transfer_env["candidates"] = [5]
    transfer_env["healthy"] = {5}
    transfer_env["servers"].clear()

    assert UserControl(1).transfer_to_free_server() == 5
    assert ("delete", 100) not in transfer_env["calls"]


def test_time_budget_stops_endless_retries(transfer_env, monkeypatch):
    """Перебор прекращается, когда исчерпан лимит времени."""
    transfer_env["candidates"] = [1, 2, 3, 4, 5]
    transfer_env["healthy"] = {5}

    clock = iter([0.0] + [100.0] * 20)
    monkeypatch.setattr(manager_users, "monotonic", lambda: next(clock))

    with pytest.raises(ServerProvisioningError):
        UserControl(1).transfer_to_free_server(time_budget=10.0)

    add_attempts = [server_id for action, server_id in transfer_env["calls"] if action == "add"]
    assert add_attempts == [1]
