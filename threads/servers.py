import time

from connect import logging
from methods.servers import check_answers_servers


def health_check_task():
    logging.info("thread health_check_task started")
    while True:
        try:
            check_answers_servers()
        except Exception as error:
            logging.error("thread health_check_task error: %s", error)
        time.sleep(60)
