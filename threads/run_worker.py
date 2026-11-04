"""Отдельный процесс фоновых задач, без gunicorn-воркеров."""

from __future__ import annotations

import os
import signal
import time


def main() -> None:
    os.environ["ENABLE_BACKGROUND_THREADS"] = "1"

    from connect import logging
    from threads import start_background_threads

    stop = {"flag": False}

    def handle_stop(signum: int, _frame: object) -> None:
        logging.info("background worker received signal %s, shutting down", signum)
        stop["flag"] = True

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    start_background_threads(daemon=True)
    logging.info("background worker started")

    while not stop["flag"]:
        time.sleep(1)


if __name__ == "__main__":
    main()
