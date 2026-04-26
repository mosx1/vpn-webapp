import time

from connect import logging
from sqlalchemy import text

from methods.manager_users import UserControl

from db.connect import SQLASession


def check_subscription():
    logging.info('thread check_subscription started')
    while True:
        try:
            db_connect = SQLASession()
            with db_connect.get_session() as session:
                data = session.execute(
                    text(
                        "SELECT server_id, array_agg(DISTINCT telegram_id) as telegram_ids" +
                        "\nFROM users_subscription" +
                        "\nWHERE action = True AND exit_date < now()" +
                        "\nGROUP BY server_id"
                    )
                )
                server_to_users_for_delete = data.fetchall()

                for server_to_users_for_delete_item in server_to_users_for_delete:
                    for telegram_id in server_to_users_for_delete_item.telegram_ids:
                        user_control = UserControl(telegram_id)
                        user_control.delete()

            time.sleep(60)
        except Exception as e:
            logging.error('thread check_subscription error: ' + str(e))