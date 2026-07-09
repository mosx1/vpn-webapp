from threading import Thread
from threads.managment_user import check_subscription
from threads.server_users_cleanup import cleanup_foreign_users_daily
# from threads.payment import check_payments


threads = [
    Thread(target=check_subscription),
    Thread(target=cleanup_foreign_users_daily)
    # Thread(target=check_payments)
]

for thread in threads:
    thread.start()