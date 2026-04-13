from threading import Thread
from threads.managment_user import check_subscription


threads = [
    Thread(target=check_subscription)
]

for thread in threads:
    thread.start()