from threading import Thread
from threads.managment_user import check_subscription
from threads.server_users_cleanup import cleanup_foreign_users_daily


threads = [
    Thread(target=check_subscription),
    Thread(target=cleanup_foreign_users_daily)
]

for thread in threads:
    thread.start()