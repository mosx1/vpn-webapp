import base64
import datetime
import uuid
import re

import jwt

from typing import Any

from flask import Blueprint, Response, render_template, request, redirect

from db.models import User, ServersTable, UserNew
from db.repository.users import UsersRepository
from db.repository.sale_invoices_in_progress import SaleInvoicesInProgressRepository
from db.repository.servers import ServersRepository
from db.repository.users_new import UsersNewRepository
from db.enums import Protocols
from db.repository.security import SecurityRepository
from db.repository.devices import Devices

from config_loader import read_config

from methods.payment.yoomoneyMethods import get_link_payment
from methods.manager_users import UserControl, get_current_user, get_link_subscription


sub = Blueprint('sub', __name__, url_prefix='/sub')

_PROTOCOL_DISPLAY: dict[int, str] = {
    Protocols.xray.value: "Xray",
    Protocols.amneziawg.value: "AmneziaWG"
}
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _decode_token(raw_jwt: str) -> dict[str, Any]:
    config = read_config()
    with SecurityRepository() as security_rep:
        return jwt.decode(
            raw_jwt,
            security_rep.get(),
            algorithms=config['JWT'].get('algoritm')
        )

@sub.route('/')
def _() -> Response:
    """
        Отдает строки для подписки
    """
    payload = {}

    conf = read_config()

    raw_jwt = request.args.get('jwt', request.args.get('token'))
    raw_jwt = raw_jwt.strip()

    with SecurityRepository() as security_rep:
        payload = jwt.decode(
            raw_jwt,
            security_rep.get(), 
            algorithms=[conf['JWT'].get('algoritm')]
        )

    with UsersRepository() as user_rep:
        user: User | None = user_rep.get_by_telegram_id(payload['telegram_id'])
        headers = {
            "subscription-userinfo": f"expire={user.exit_date.timestamp()};",
            "support-url": "https://t.me/open_vpn_sale_bot",
            "profile-update-interval": 1,
            "profile-web-page-url": f"https://{conf['BaseConfig'].get('host')}/sub/home?token={raw_jwt}"
        }
        subscription_data = base64.b64encode(user.server_link.encode("utf-8")).decode("utf-8")
        if user.protocol == Protocols.amneziawg.value:
            headers['announce'] = "The AmnesiaWG protocol is selected in the profile. Download the AmnesiaWG app and set it up.".encode("ascii")
            subscription_data = None
        return Response(
            subscription_data,
            headers=headers
        )


@sub.route('/mobile')
def linkIphone() -> Response:
    """
        Создает ссылку для подписки
    """

    config = read_config()

    request.headers.get('User-Agent')
    device_client: str = (request.headers.get('User-Agent').split("(")[1]).split(";")[0]

    match device_client:
        
        case Devices.iphone.value | Devices.macintosh.value | Devices.android.value:
            deeplink_start = 'happ://crypt/'

        case Devices.windows.value:
            deeplink_start = 'hiddify://import/'

        case _:
            return Response('Воспользуйтесь ручной настройкой')
    
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
def home_page() -> Response:
    
    config = read_config()
    raw_jwt = request.args.get('token').strip()
    email = None
    data_from_jwt = _decode_token(raw_jwt)
    with UsersRepository() as user_rep:
        user: User = user_rep.get_by_telegram_id(data_from_jwt['telegram_id'])
    with ServersRepository() as server_rep:
        server: ServersTable = server_rep.get_by_id(user.server_id)
    is_admin = False
    with UsersNewRepository() as users_new_repo:
        users_new: UserNew | None = users_new_repo.get_by_id(data_from_jwt['telegram_id'])
        if users_new:
            email = users_new.email
            is_admin = email.strip().lower() == config['BaseConfig'].get('admin_email')
    aw: bool = user.protocol == Protocols.amneziawg.value
    sub_link = f"happ://add/https://kuzmos.ru/sub?token={raw_jwt}"
    param_aw = ""
    if aw:
        param_aw = f"?aw={aw}"

    app_link = f"/download_app{param_aw}"
    pay_link = f"/sub/pay?token={raw_jwt}&month=1"
    month_price = config['Price'].getint('RUB')

    link: str = get_link_subscription(data_from_jwt['telegram_id'])
    protocol_name = _PROTOCOL_DISPLAY.get(user.protocol, str(user.protocol))
    subscription_exit: bool = user.exit_date > datetime.datetime.now()
    referal_code: str = f'https://{config["BaseConfig"].get("host")}?referal={user.telegram_id}'
    
    return Response(
        render_template(
            'sub_home.html',
            sub_link=sub_link,
            app_link=app_link,
            pay_link=pay_link,
            month_price=month_price,
            server_name=server.name,
            user=user,
            sub_url_manual=link,
            token=raw_jwt,
            protocol_name=protocol_name,
            subscription_exit=subscription_exit,
            email=email,
            is_admin=is_admin,
            referal_code=referal_code
        )
    )


@sub.route('/transfer_other_server')
def transfer_other_server() -> Response:

    raw_jwt = request.args.get('token').strip()
    user: User = get_current_user()
    
    with ServersRepository() as server_rep:
        server_id: int = server_rep.get_very_free_server(exclude_server_id=user.server_id)
    user_control = UserControl(user.telegram_id)
    user_control.update_server(server_id)
    return redirect(f"/sub/home?token={raw_jwt}")


@sub.route('/pay')
def payment() -> Response:

    config = read_config()

    label = str(uuid.uuid4())
    raw_jwt = request.args.get('token').strip()

    month_raw = request.args.get('month', '1').strip()
    try:
        count_month = int(month_raw)
    except ValueError:
        return Response("Invalid month count", status=400)
    if count_month < 1:
        return Response("Month count must be greater than 0", status=400)

    is_gift = request.args.get('gift', '0').strip() == '1'
    gift_email = request.args.get('gift_email', '').strip().lower()
    with SecurityRepository() as security_rep:
        data_from_jwt: dict[str, Any] = jwt.decode(
            raw_jwt,
            security_rep.get(), 
            algorithms=config['JWT'].get('algoritm')
        )

    if is_gift and not _EMAIL_PATTERN.fullmatch(gift_email):
        return Response("Invalid recipient email", status=400)

    with ServersRepository() as servers_repo:
        very_free_server_id = servers_repo.get_very_free_server()

    with SaleInvoicesInProgressRepository() as siip_repo:
        siip_repo.add_sale_invoice(
            label,
            data_from_jwt['telegram_id'],
            very_free_server_id,
            count_month,
            is_gift=is_gift,
            gift_recipient_email=gift_email if is_gift else None
        )

    link = get_link_payment(
        label, 
        count_month
    )

    return redirect(
        link
    )


@sub.route("/transfer_protocol")
def transfer_protocol() -> Response:

    raw_jwt = request.args.get('token').strip()
    user: User = get_current_user()
    match user.protocol:
        case Protocols.xray.value:
            new_protocol = Protocols.amneziawg
        case Protocols.amneziawg.value:
            new_protocol = Protocols.xray

    user_control = UserControl(user.telegram_id)
    user_control.update_protocol(new_protocol)
    
    return redirect(f'/sub/home?token={raw_jwt}')


@sub.route('/resume')
def resume() -> Response:
    raw_jwt = request.args.get('token').strip()
    user: User = get_current_user()

    user_control = UserControl(user.telegram_id)
    user_control.add(user.server_id)

    return redirect(f'/sub/home?token={raw_jwt}')