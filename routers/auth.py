import jwt

from flask import Blueprint, Response, render_template, request

from methods.mail.email_sender import send_yandex_email
from methods.manager_users import UserControl, get_current_user, get_link_subscription

from db.repository.users_new import UsersNewRepository
from db.repository.security import SecurityRepository
from db.models import UserNew

from connect import config

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/')
def auth_main() -> Response:
    return Response(render_template('auth/auth.html'))


@auth.route('/confirm_email')
def confirm_email() -> Response:
    email = request.args.get('email').strip()
    user_id: int | None = None
    with UsersNewRepository() as users_new_repo:
        user = users_new_repo.get_one(UserNew.email == email)
        if user:
            user_id = user.telegram_id
    if not user_id:
        user_id = UserControl.create(email)
    with SecurityRepository() as security_rep:
        token: str = jwt.encode(
            {"telegram_id": user_id},
            security_rep.get(), 
            algorithm=config['JWT'].get('algoritm')
        )
    send_yandex_email(
        to_email=email,
        subject="Выгодный VPN. Личный кабинет",
        text_body=f"Ваша персональная ссылка для входа в личный кабинет: https://kuzmos.ru/sub/home?token={token}",
    )
    return Response(
        render_template('auth/auth_end.html')
    )