import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('APP_PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", max(2, multiprocessing.cpu_count())))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
threads = int(os.getenv("GUNICORN_THREADS", "8"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
proxy_allow_ips = forwarded_allow_ips


def post_fork(server, worker):
    # В docker-compose фоновые задачи идут в сервис worker (ENABLE_BACKGROUND_THREADS=0 у web).
    if os.getenv("ENABLE_BACKGROUND_THREADS", "1") != "1":
        return

    lock_path = os.getenv("BACKGROUND_THREADS_LOCK", "/tmp/vpn-webapp-bg.lock")
    try:
        lock_file = open(lock_path, "w")
        import fcntl

        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        return

    from threads import start_background_threads

    start_background_threads()
    worker.log.info("Background threads started in worker pid=%s", worker.pid)
