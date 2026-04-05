import base64, jwt, uuid

from typing import Any

from flask import Blueprint, Response, render_template, request, redirect

from db.models import User
from db.repository.users import UsersRepository
from db.repository.sale_invoices_in_progress import SaleInvoicesInProgressRepository
from db.repository.servers import ServersRepository

from db.repository.security import SecurityRepository
from db.repository.devices import Devices

from configparser import ConfigParser

from methods.payment.yoomoneyMethods import get_link_payment


sub = Blueprint('sub', __name__, url_prefix='/sub')


def get_link_subscription(telegram_id: str | int) -> str:
    """
        Отдает ссылку для получения подписки
    """
    config = ConfigParser()
    config.read('config.ini')

    with SecurityRepository() as security_rep:
        token: str = jwt.encode(
            {"telegram_id": telegram_id},
            security_rep.get(), 
            algorithm=config['JWT'].get('algoritm')
        )

        return f"https://kuzmos.ru/sub?jwt={token}"


@sub.route('/')
def _() -> Response:
    """
        Отдает строки для подписки
    """
    payload = {}

    conf = ConfigParser()
    conf.read('config.ini')

    raw_jwt = request.args.get('jwt').strip()

    with SecurityRepository() as security_rep:
        payload = jwt.decode(
            raw_jwt,
            security_rep.get(), 
            algorithms=[conf['JWT'].get('algoritm')]
        )

    with UsersRepository() as user_rep:
        user: User | None = user_rep.get_by_telegram_id(payload['telegram_id'])
        
        return Response(
            base64.b64encode(user.server_link.encode("utf-8")).decode("utf-8"),
            headers={
                "subscription-userinfo": f"expire={user.exit_date.timestamp()};",
                "support-url": "https://t.me/open_vpn_sale_bot",
                "profile-update-interval": 1,
                "profile-web-page-url": "https://t.me/open_vpn_sale_bot"
            }
        )
    

# @sub.route('/get_link')
# def get_link() -> Response:
#     return Response(get_link_subscription(request.args.get('id')))


@sub.route('/mobile')
def linkIphone() -> Response:
    """
        Создает ссылку для подписки
    """

    config = ConfigParser()
    config.read('config.ini')

    request.headers.get('User-Agent')
    device_client: str = (request.headers.get('User-Agent').split("(")[1]).split(";")[0]

    match device_client:
        
        case Devices.iphone.value | Devices.macintosh.value | Devices.android.value:
            deeplink_start = 'happ://crypt/'

        case Devices.windows.value:
            deeplink_start = 'hiddify://import/'

        case _:
            return Response('Воспользуйтесь ручной наастройкой')
    
    raw_jwt = request.args.get('token').strip()

    with SecurityRepository() as security_rep:
        data_from_jwt: dict[str, Any] = jwt.decode(
            raw_jwt,
            security_rep.get(), 
            algorithms=config['JWT'].get('algoritm')
        )
    
    link: str = get_link_subscription(data_from_jwt['telegram_id'])

    return redirect(deeplink_start + link)


@sub.route('/home')
def home_page() -> str | Response:

    config = ConfigParser()
    config.read('config.ini')

    raw_jwt = request.args.get('token').strip()

    with SecurityRepository() as security_rep:
        data_from_jwt: dict[str, Any] = jwt.decode(
            raw_jwt,
            security_rep.get(), 
            algorithms=config['JWT'].get('algoritm')
        )
    with UsersRepository() as user_rep:
        user: User = user_rep.get_by_telegram_id(data_from_jwt['telegram_id'])

    sub = f"happ://add/https://kuzmos.ru/sub?token={raw_jwt}"
    app_link = f"https://{config['BaseConfig'].get('host')}/download_app"
    pay_link = f"https://{config['BaseConfig'].get('host')}/sub/pay?token={raw_jwt}&month=1"

    link: str = get_link_subscription(data_from_jwt['telegram_id'])

    return Response(
        render_template(
            'sub_home.html',
            sub_link=sub,
            app_link=app_link,
            pay_link=pay_link,
            user=user,
            sub_url_manual=link
        )
    )

@sub.route('/pay')
def payment() -> Response:

    config = ConfigParser()
    config.read('config.ini')

    label = str(uuid.uuid4())
    raw_jwt = request.args.get('token').strip()

    count_month = int(request.args.get('month'))
    with SecurityRepository() as security_rep:
        data_from_jwt: dict[str, Any] = jwt.decode(
            raw_jwt,
            security_rep.get(), 
            algorithms=config['JWT'].get('algoritm')
        )
    with ServersRepository() as servers_repo:
        very_free_server_id = servers_repo.get_very_free_server()

    with SaleInvoicesInProgressRepository() as siip_repo:
        siip_repo.add_sale_invoice(
            label,
            data_from_jwt['telegram_id'],
            very_free_server_id,
            count_month
        )

    link = get_link_payment(
        label, 
        count_month
    )

    return redirect(
        link
    )