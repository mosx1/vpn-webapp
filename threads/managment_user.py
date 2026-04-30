import time

from connect import logging

from methods.manager_users import UserControl
from methods.mail.email_sender import send_yandex_email

from db.repository.users import UsersRepository


def _notify_expiring_users(users_repo: UsersRepository) -> None:
    reminder_windows = [
        (
            "3 days",
            "Ваша подписка истекает через 3 дня",
            "Напоминаем: ваша VPN-подписка истекает через 3 дня.",
        ),
        (
            "2 days",
            "Ваша подписка истекает через 2 дня",
            "Напоминаем: ваша VPN-подписка истекает через 2 дня.",
        ),
        (
            "1 day",
            "Ваша подписка истекает через 1 день",
            "Напоминаем: ваша VPN-подписка истекает через 1 день.",
        ),
        (
            "1 hour",
            "Ваша подписка истекает через 1 час",
            "Напоминаем: ваша VPN-подписка истекает через 1 час.",
        ),
    ]

    for interval_value, subject, message in reminder_windows:
        reminder_data = users_repo.get_active_users_with_email_expiring_in(
            interval_value=interval_value,
            window_minutes=1
        )

        for row in reminder_data:
            try:
                send_yandex_email(
                    to_email=row.email,
                    subject=subject,
                    text_body=message,
                )
            except Exception as e:
                logging.error(
                    f"cannot send reminder '{interval_value}' "
                    f"for telegram_id={row.telegram_id}: {e}"
                )

    now_data = users_repo.get_active_users_with_email_expiring_now(window_minutes=1)

    for row in now_data:
        try:
            send_yandex_email(
                to_email=row.email,
                subject="Ваша подписка заканчивается прямо сейчас",
                text_body="Срок вашей VPN-подписки заканчивается прямо сейчас.",
            )
        except Exception as e:
            logging.error(f"cannot send now reminder for telegram_id={row.telegram_id}: {e}")


def check_subscription():
    logging.info('thread check_subscription started')
    while True:
        try:
            with UsersRepository() as users_repo:
                _notify_expiring_users(users_repo)
                server_to_users_for_delete = users_repo.get_expired_active_users_grouped_by_server()

                for server_to_users_for_delete_item in server_to_users_for_delete:
                    for telegram_id in server_to_users_for_delete_item.telegram_ids:
                        user_control = UserControl(telegram_id)
                        user_control.delete()

            time.sleep(60)
        except Exception as e:
            logging.error('thread check_subscription error: ' + str(e))