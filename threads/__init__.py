import os
from threading import Thread

from threads.managment_user import check_subscription
from threads.server_users_cleanup import cleanup_foreign_users_daily
from threads.servers import health_check_task

_background_threads_started = False


def start_background_threads() -> None:
    global _background_threads_started
    if _background_threads_started:
        return
    if os.getenv("ENABLE_BACKGROUND_THREADS", "1") != "1":
        return

    threads = [
        Thread(target=check_subscription, daemon=True),
        Thread(target=cleanup_foreign_users_daily, daemon=True),
        Thread(target=health_check_task, daemon=True),
    ]
    for thread in threads:
        thread.start()
    _background_threads_started = True
