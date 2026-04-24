import hashlib
import jwt
import secrets
import threading
import time

from flask import Blueprint, Response, render_template, request

from methods.mail.email_sender import send_yandex_email
from methods.manager_users import UserControl

from db.repository.users_new import UsersNewRepository
from db.repository.security import SecurityRepository
from db.models import UserNew

from connect import config

auth = Blueprint('auth', __name__, url_prefix='/auth')
_CAPTCHA_TTL_SECONDS = 5 * 60
_captcha_store: dict[str, tuple[str, float]] = {}
_captcha_lock = threading.Lock()


def _cleanup_expired_captcha() -> None:
    now = time.time()
    with _captcha_lock:
        expired_nonces = [
            nonce
            for nonce, (_, created_at) in _captcha_store.items()
            if now - created_at > _CAPTCHA_TTL_SECONDS
        ]
        for nonce in expired_nonces:
            _captcha_store.pop(nonce, None)


def _create_captcha() -> tuple[str, str]:
    _cleanup_expired_captcha()
    nonce = secrets.token_urlsafe(12)
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    code = "".join(secrets.choice(alphabet) for _ in range(5))
    with _captcha_lock:
        _captcha_store[nonce] = (code, time.time())
    return nonce, code


def _build_captcha_svg(code: str, nonce: str) -> str:
    digest = hashlib.sha256(f"{nonce}:{code}".encode("utf-8")).digest()
    width, height = 180, 60

    line_chunks: list[str] = []
    for index in range(6):
        start_x = digest[index] % width
        start_y = digest[index + 6] % height
        end_x = digest[index + 12] % width
        end_y = digest[index + 18] % height
        opacity = 0.20 + ((digest[index + 24] % 30) / 100)
        line_chunks.append(
            f'<line x1="{start_x}" y1="{start_y}" x2="{end_x}" y2="{end_y}" '
            f'stroke="#64748b" stroke-width="1.4" opacity="{opacity:.2f}"/>'
        )

    text_chunks: list[str] = []
    for index, char in enumerate(code):
        x_pos = 18 + index * 31
        y_shift = (digest[index + 2] % 15) - 7
        rotation = (digest[index + 9] % 30) - 15
        text_chunks.append(
            f'<text x="{x_pos}" y="{36 + y_shift}" font-size="30" '
            f'font-family="Arial, sans-serif" font-weight="700" fill="#0f172a" '
            f'transform="rotate({rotation} {x_pos} {36 + y_shift})">{char}</text>'
        )

    noise_chunks: list[str] = []
    for index in range(35):
        x_pos = digest[index % len(digest)] % width
        y_pos = digest[(index + 5) % len(digest)] % height
        radius = 0.7 + (digest[(index + 11) % len(digest)] % 20) / 20
        noise_chunks.append(
            f'<circle cx="{x_pos}" cy="{y_pos}" r="{radius:.2f}" '
            f'fill="#94a3b8" opacity="0.30"/>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="captcha">'
        '<rect width="100%" height="100%" fill="#f8fafc" rx="10"/>'
        f'{"".join(line_chunks)}{"".join(noise_chunks)}{"".join(text_chunks)}'
        "</svg>"
    )


def _validate_captcha(captcha_nonce: str, captcha_code: str) -> bool:
    if not captcha_nonce or not captcha_code:
        return False
    with _captcha_lock:
        stored = _captcha_store.pop(captcha_nonce, None)
    if not stored:
        return False
    expected_code, created_at = stored
    if time.time() - created_at > _CAPTCHA_TTL_SECONDS:
        return False
    return expected_code == captcha_code.strip().upper()


@auth.route('/')
def auth_main() -> Response:
    captcha_nonce, _ = _create_captcha()
    return Response(
        render_template(
            'auth/auth.html',
            captcha_nonce=captcha_nonce,
            email_value='',
            captcha_error='',
        )
    )


@auth.route('/captcha')
def captcha_image() -> Response:
    captcha_nonce = request.args.get('nonce', '').strip()
    with _captcha_lock:
        stored = _captcha_store.get(captcha_nonce)
    if not stored:
        return Response("Captcha expired", status=404, mimetype="text/plain")

    captcha_code, created_at = stored
    if time.time() - created_at > _CAPTCHA_TTL_SECONDS:
        with _captcha_lock:
            _captcha_store.pop(captcha_nonce, None)
        return Response("Captcha expired", status=404, mimetype="text/plain")

    svg = _build_captcha_svg(captcha_code, captcha_nonce)
    return Response(svg, mimetype="image/svg+xml")


@auth.route('/confirm_email')
def confirm_email() -> Response:
    email = request.args.get('email', '').strip()
    captcha_code = request.args.get('captcha_code', '').strip()
    captcha_nonce = request.args.get('captcha_nonce', '').strip()

    if not email:
        new_captcha_nonce, _ = _create_captcha()
        return Response(
            render_template(
                'auth/auth.html',
                captcha_nonce=new_captcha_nonce,
                email_value='',
                captcha_error='Введите email.',
            )
        )

    if not _validate_captcha(captcha_nonce, captcha_code):
        new_captcha_nonce, _ = _create_captcha()
        return Response(
            render_template(
                'auth/auth.html',
                captcha_nonce=new_captcha_nonce,
                email_value=email,
                captcha_error='Капча введена неверно или устарела. Попробуйте снова.',
            )
        )

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
    return Response(render_template('auth/auth_end.html'))