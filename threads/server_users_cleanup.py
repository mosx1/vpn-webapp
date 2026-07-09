import time

from connect import logging
from db.enums import PanelXray
from db.models import ServersTable
from db.repository.servers import ServersRepository
from db.repository.users import UsersRepository
from methods.controller_3x_ui import UserControl3xUI
from methods.controller_manager_xray_api import UserControlXray

_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60


def _get_cleanup_controller(server: ServersTable):
    if server.panel_xray == PanelXray.xray.value:
        return UserControlXray
    if server.panel_xray == PanelXray.xui.value:
        return UserControl3xUI
    return None


def _cleanup_server_users_once() -> None:
    with ServersRepository() as servers_repo:
        servers: list[ServersTable] = servers_repo.get_all()

    with UsersRepository() as users_repo:
        all_user_ids = set(users_repo.get_all_telegram_ids())
        server_to_user_ids: dict[int, set[int]] = {
            server.id: set(users_repo.get_telegram_ids_by_server_id(server.id))
            for server in servers
        }

    for server in servers:
        expected_user_ids = server_to_user_ids.get(server.id, set())
        users_not_related_to_server = all_user_ids - expected_user_ids
        if not users_not_related_to_server:
            continue

        cleanup_controller = _get_cleanup_controller(server)
        if cleanup_controller is None:
            logging.warning(
                "skip foreign users cleanup for server_id=%s: unknown panel_xray=%s",
                server.id,
                server.panel_xray
            )
            continue

        try:
            cleanup_controller.delete(users_not_related_to_server, server.id)
            logging.info(
                "foreign users cleanup done for server_id=%s, candidates=%s",
                server.id,
                len(users_not_related_to_server)
            )
        except Exception as error:
            logging.error(
                "foreign users cleanup failed for server_id=%s: %s",
                server.id,
                error
            )


def cleanup_foreign_users_daily() -> None:
    logging.info("thread cleanup_foreign_users_daily started")
    while True:
        started_at = time.time()
        try:
            _cleanup_server_users_once()
        except Exception as error:
            logging.error("thread cleanup_foreign_users_daily error: %s", error)

        elapsed_seconds = int(time.time() - started_at)
        sleep_seconds = max(60, _CLEANUP_INTERVAL_SECONDS - elapsed_seconds)
        time.sleep(sleep_seconds)
