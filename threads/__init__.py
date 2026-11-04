import os
from threading import Thread

from threads.managment_user import check_subscription
from threads.server_users_cleanup import cleanup_foreign_users_daily
from threads.servers import health_check_task

_background_threads_started = False
_background_threads: list[Thread] = []


def start_background_threads(*, daemon: bool = True) -> None:
    global _background_threads_started
    if _background_threads_started:
        return
    if os.getenv("ENABLE_BACKGROUND_THREADS", "1") != "1":
        return

    threads = [
        Thread(target=check_subscription, name="check_subscription", daemon=daemon),
        Thread(
            target=cleanup_foreign_users_daily,
            name="cleanup_foreign_users_daily",
            daemon=daemon,
        ),
        Thread(target=health_check_task, name="health_check_task", daemon=daemon),
    ]
    for thread in threads:
        thread.start()
        _background_threads.append(thread)
    _background_threads_started = True


def wait_background_threads() -> None:
    for thread in list(_background_threads):
        thread.join()
