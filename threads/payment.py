import time

from connect import logging

from db.models import User, SaleInvoicesInProgress, UserNew

from methods.payment.yoomoneyMethods import getInfoLastPayment

from configparser import ConfigParser

from db.repository.sale_invoices_in_progress import SaleInvoicesInProgressRepository
from db.repository.users import UsersRepository
from db.repository.users_new import UsersNewRepository

from methods.manager_users import UserControl
from methods.mail.email_sender import send_yandex_email


def check_payments() -> None:

    config = ConfigParser()
    config.read('config.ini')

    while True:
        
        with SaleInvoicesInProgressRepository() as siip_repo:

            invoices = siip_repo.get_sale_invoice_by_label()
            
            for invoice_item in invoices:
                
                invoice: SaleInvoicesInProgress = invoice_item[0]
                stop_date_time = invoice_item[1]
                current_date_time = invoice_item[2]

                try:
                    info_last_payment: dict | None = getInfoLastPayment(invoice.label)
                except Exception as e:
                    print(str(e))
                    continue
                
                if not invoice.is_gift and info_last_payment and invoice.server_id:
                    success_payment(invoice)
                # if invoice.is_gift and (invoice.telegram_id == config['Telegram'].getint('admin_chat') or (info_last_payment and not invoice.server_id)):
                #     success_payment_gift(invoice, config)

                if (
                    current_date_time.strftime("%Y-%m-%d %H:%M:%S") > stop_date_time.strftime("%Y-%m-%d %H:%M:%S")
                    ) or info_last_payment or (
                        invoice.telegram_id == config['Telegram'].getint('admin_chat') and invoice.is_gift
                    ):
                    siip_repo.delete(invoice.id)

            time.sleep(2)


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

        with SaleInvoicesInProgressRepository() as siip_repo:
            siip_repo.delete(invoice.id)


# def success_payment_gift(invoice: SaleInvoicesInProgress, config: ConfigParser):
#     """
#     Process successful gift payment with proper error handling and file handle management.
#     """
#     user: User | None = get_user_by_id(invoice.telegram_id)

#     if not user:
#         logging.error(f'User not found for gift invoice {invoice.id}, telegram_id: {invoice.telegram_id}')
#         return

#     logging.info(
#         "user_id: {}; user_name:{}; Оплата подарочной подписки {} мес.".format(
#             user.telegram_id,
#             user.name,
#             invoice.month_count
#         )
#     )

#     # Step 1: Generate gift code
#     try:
#         hash = genGiftCode(invoice.month_count)
#     except Exception as e:
#         logging.error(f'Failed to generate gift code for invoice {invoice.id}: {str(e)}')
#         bot.send_message(
#             config['Telegram']['admin_chat'],
#             f'Ошибка генерации подарочного кода\nпоток: check_payments\nerror: ```' + utils.form_text_markdownv2(str(e)) + "```"
#         )
#         return

#     # Step 2: Notify admin about gift purchase
#     try:
#         bot.send_message(
#             config['Telegram'].getint('admin_chat'),
#             "[{}](tg://user?id\={}) оплатил подарочную подписку".format(utils.form_text_markdownv2(user.name), user.telegram_id),
#             parse_mode=ParseMode.mdv2.value
#         )
#     except Exception as e:
#         logging.error(f'Failed to notify admin about gift purchase by {user.telegram_id}: {str(e)}')

#     # Step 3: Delete payment message
#     try:
#         bot.delete_message(
#             invoice.chat_id,
#             invoice.message_id
#         )
#     except Exception as e:
#         logging.error(f'Failed to delete gift payment message: {str(e)}')

#     # Step 4: Get MTProto URL
#     try:
#         mtproto = get_url_mtproto(user.server_id)
#     except Exception as e:
#         logging.error(f'Failed to get MTProto URL for server {user.server_id}: {str(e)}')
#         mtproto = "Недоступно"

#     # Step 5: Send gift photo with proper file handle management
#     photoMessage: Message | None = None

#     with open("static/logo_big.jpeg", "rb") as photo:
#         photoMessage = bot.send_photo(
#             chat_id=user.telegram_id,
#             photo=photo,
#             caption=config['MessagesTextMD'].get('gift_postcard').format(
#                 code=hash,
#                 date=invoice.month_count,
#                 mtproto=mtproto
#             ),
#             parse_mode=ParseMode.mdv2.value
#         )

#     # Step 6: Send reply message
#     try:
#         bot.reply_to(
#             photoMessage,
#             "Перешлите это сообщение другу в качестве подарка. Спасибо что помогаете нам делать интернет доступнее."
#         )
#     except Exception as e:
#         logging.error(f'Failed to send reply to gift message for {user.telegram_id}: {str(e)}')

#     # Step 7: Final admin notification
#     try:
#         bot.send_message(
#             config['Telegram']['admin_chat'],
#             "[" + utils.form_text_markdownv2(user.name) + "](tg://user?id\=" + str(user.telegram_id) + ") оплатил подарочную подписку",
#             parse_mode=ParseMode.mdv2.value
#         )
#     except Exception as e:
#         logging.error(f'Failed to send final admin notification for gift by {user.telegram_id}: {str(e)}')

#     # Step 8: Delete invoice after successful completion
#     del_invoice(invoice)