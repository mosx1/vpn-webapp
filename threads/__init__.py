from threading import Thread
from threads.managment_user import check_subscription
from threads.payment import check_payments


threads = [
    Thread(target=check_subscription),
    Thread(target=check_payments)
]

for thread in threads:
    thread.start()