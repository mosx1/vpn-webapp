import jwt
import time
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from db.models import SaleInvoicesInProgress, User, UserNew
from db.repository.users import UsersRepository
from db.repository.users_new import UsersNewRepository
from db.repository.security import SecurityRepository
from db.repository.sale_invoices_in_progress import SaleInvoicesInProgressRepository
from config_loader import read_config

from methods.manager_users import UserControl
from methods.mail.email_sender import send_yandex_email
from connect import logging


def success_payment(invoice: SaleInvoicesInProgress):
    with UsersRepository() as users_repo:
        user: User | None = users_repo.get_by_telegram_id(invoice.telegram_id)

        if not user:
            logging.error(f'User not found for invoice {invoice.id}, telegram_id: {invoice.telegram_id}')
            return

        logging.info(
            "user_id: {}; user_name:{}; Оплата подписки {} мес. сервер {}".format(
                user.telegram_id,
                user.name,
                invoice.month_count,
                invoice.server_id
            )
        )
    
        with UsersNewRepository() as users_new_repo:
            users_new: UserNew | None = users_new_repo.get_by_id(user.telegram_id)
            if users_new:
                send_yandex_email(
                    users_new.email, 
                    "Оплата подписки", 
                    "Ваша подписка продлена"
                )
        user_control = UserControl(user.telegram_id)
        user_control.prolongation(invoice.month_count * 30)
        if not user.action:
            user_control.add(invoice.server_id)

        delete_invoice(invoice)


def success_payment_gift(invoice: SaleInvoicesInProgress) -> None:
    recipient_email = (invoice.gift_recipient_email or '').strip().lower()
    if not recipient_email:
        logging.error(f'Recipient email is empty for gift invoice {invoice.id}')
        return

    recipient_user_id: int | None = None
    with UsersNewRepository() as users_new_repo:
        recipient_user = users_new_repo.get_one(UserNew.email == recipient_email)
        if recipient_user:
            recipient_user_id = recipient_user.telegram_id

    if not recipient_user_id:
        recipient_user_id = UserControl.create(recipient_email)

    user_control = UserControl(recipient_user_id)
    user_control.prolongation(invoice.month_count * 30)

    with UsersRepository() as users_repo:
        recipient_subscription: User | None = users_repo.get_by_telegram_id(recipient_user_id)
        if recipient_subscription and not recipient_subscription.action:
            user_control.add(recipient_subscription.server_id)

    config = read_config()
    with SecurityRepository() as security_rep:
        token: str = jwt.encode(
            {"telegram_id": recipient_user_id},
            security_rep.get(),
            algorithm=config['JWT'].get('algoritm')
        )

    send_yandex_email(
        to_email=recipient_email,
        subject="Вам подарили VPN подписку",
        text_body=(
            "Для входа в личный кабинет перейдите по ссылке: "
            f"https://kuzmos.ru/sub/home?token={token}"
        )
    )
    delete_invoice(invoice)


def delete_invoice(invoice: SaleInvoicesInProgress) -> None:
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        with SaleInvoicesInProgressRepository() as siip_repo:
            try:
                # Don't block worker forever if row is locked by another transaction.
                siip_repo.session.execute(text("SET LOCAL lock_timeout = '5s'"))
                deleted = siip_repo.delete(int(invoice.id))
                siip_repo.session.commit()
                if not deleted:
                    logging.warning(f'Invoice already removed or not found: id={invoice.id}, label={invoice.label}')
                return
            except OperationalError as e:
                siip_repo.session.rollback()
                if attempt == max_attempts:
                    logging.error(
                        f'Failed to delete invoice after {max_attempts} attempts '
                        f'id={invoice.id}, label={invoice.label}: {e}'
                    )
                    return
                time.sleep(0.35 * attempt)