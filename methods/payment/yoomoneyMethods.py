from yoomoney import History, Quickpay, Client

from config_loader import read_config

from connect import logging
from methods.payment.common import get_success_payment_url


def getInfoLastPayment(label: str) -> dict:
    """
        Получает информацию о последнем платеже по идентификатору платежа
    """
    conf = read_config()
    client = Client(conf['YooMoney'].get('token'))
    history: History = client.operation_history(label=label)
    
    for operation in history.operations:

        return {
            "status": operation.status,
            "message": "{}\nstatus: {}\ndatetime: {}\nсумма: {}".format(
                operation.title,
                operation.status,
                operation.datetime,
                operation.amount
            )
        }


def get_link_payment(label: str, month: int) -> str:
    """
        Создает ссылку на платеж
    """
    conf = read_config()

    quickpay = Quickpay(
        receiver=conf['YooMoney'].get('WALLET_YOOMONEY_ID'),
        quickpay_form="shop",
        targets="Оплата VPN",
        paymentType="SB",
        sum=conf['Price'].getint('RUB') * month,
        label=label,
        successURL=get_success_payment_url(),
    )

    return quickpay.redirected_url