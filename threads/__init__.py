from threading import Thread
from threads.managment_user import check_subscription
from threads.server_users_cleanup import cleanup_foreign_users_daily
from threads.servers import health_check_task


threads = [
    Thread(target=check_subscription),
    Thread(target=cleanup_foreign_users_daily),
    Thread(target=health_check_task)
]

for thread in threads:
    thread.start()