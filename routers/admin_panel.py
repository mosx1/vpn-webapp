import jwt

from typing import Any
from pathlib import Path

from flask import Blueprint, Response, render_template, request, redirect, send_file, jsonify
from sqlalchemy import select, or_, func

from db.models import User, UserNew, ServersTable
from db.repository.users import UsersRepository
from db.repository.users_new import UsersNewRepository
from db.repository.servers import ServersRepository
from db.repository.security import SecurityRepository
from db.enums import Protocols

from config_loader import read_config
from methods.manager_users import UserControl


admin_panel_bp = Blueprint('admin_panel_bp', __name__, url_prefix='/admin')
_ADMIN_EMAIL = "597730754a@gmail.com"
_LOG_FILE_PATH = Path(__file__).resolve().parent.parent / "logs.txt"
_USERS_PAGE_SIZE = 50


def _read_token_from_request() -> str:
    raw = request.values.get('token', '')
    return raw.strip()


def _decode_token(raw_jwt: str) -> dict[str, Any]:
    config = read_config()
    with SecurityRepository() as security_rep:
        return jwt.decode(
            raw_jwt,
            security_rep.get(),
            algorithms=config['JWT'].get('algoritm')
        )


def _is_admin_by_telegram_id(telegram_id: int) -> bool:
    with UsersNewRepository() as users_new_repo:
        users_new: UserNew | None = users_new_repo.get_by_id(telegram_id)
    if not users_new or not users_new.email:
        return False
    return users_new.email.strip().lower() == _ADMIN_EMAIL


def _build_users_stmt(search_query: str):
    stmt = (
        select(User, UserNew.email)
        .outerjoin(UserNew, UserNew.telegram_id == User.telegram_id)
        .order_by(User.exit_date.asc())
    )
    if search_query:
        pattern = f"%{search_query.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(func.coalesce(User.name, '')).like(pattern),
                func.lower(func.coalesce(UserNew.email, '')).like(pattern)
            )
        )
    return stmt


def _serialize_user_item(user_item) -> dict[str, Any]:
    user: User = user_item[0]
    user_email: str | None = user_item[1]
    return {
        "telegram_id": user.telegram_id,
        "name": user.name or "Без имени",
        "email": user_email or "Email не указан",
        "exit_date": user.exit_date.strftime('%d.%m.%Y'),
        "action": bool(user.action),
        "server_id": user.server_id,
        "protocol": user.protocol,
        "server_link": user.server_link,
    }


def _get_users_page(search_query: str, offset: int, limit: int):
    with UsersRepository() as users_repo:
        stmt = _build_users_stmt(search_query)
        rows = users_repo.session.execute(stmt.offset(offset).limit(limit + 1)).fetchall()
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    return page_rows, has_more


@admin_panel_bp.route('/')
def admin_panel() -> Response:
    raw_jwt = _read_token_from_request()
    if not raw_jwt:
        return Response("Token is required", status=400)

    data_from_jwt = _decode_token(raw_jwt)
    telegram_id = data_from_jwt['telegram_id']
    if not _is_admin_by_telegram_id(telegram_id):
        return Response("Forbidden", status=403)

    search_query = request.args.get('q', '').strip()
    with ServersRepository() as servers_repo:
        servers = servers_repo.session.execute(
            select(ServersTable).order_by(ServersTable.name.asc())
        ).scalars().all()

    users_data, has_more = _get_users_page(
        search_query=search_query,
        offset=0,
        limit=_USERS_PAGE_SIZE
    )

    return Response(
        render_template(
            'admin_panel.html',
            token=raw_jwt,
            users_data=users_data,
            search_query=search_query,
            servers=servers,
            protocol_options=[
                (Protocols.xray.value, "Xray"),
                (Protocols.amneziawg.value, "AmneziaWG")
            ],
            users_has_more=has_more,
            users_page_size=_USERS_PAGE_SIZE
        )
    )


@admin_panel_bp.route('/users')
def admin_users_page() -> Response:
    raw_jwt = _read_token_from_request()
    if not raw_jwt:
        return Response("Token is required", status=400)

    data_from_jwt = _decode_token(raw_jwt)
    if not _is_admin_by_telegram_id(data_from_jwt['telegram_id']):
        return Response("Forbidden", status=403)

    search_query = request.args.get('q', '').strip()
    offset_raw = request.args.get('offset', '0').strip()
    try:
        offset = max(0, int(offset_raw))
    except ValueError:
        return Response("Invalid offset", status=400)

    users_data, has_more = _get_users_page(
        search_query=search_query,
        offset=offset,
        limit=_USERS_PAGE_SIZE
    )

    return jsonify(
        {
            "users": [_serialize_user_item(item) for item in users_data],
            "has_more": has_more
        }
    )


@admin_panel_bp.route('/user-action', methods=['POST'])
def admin_user_action() -> Response:
    raw_jwt = _read_token_from_request()
    if not raw_jwt:
        return Response("Token is required", status=400)

    data_from_jwt = _decode_token(raw_jwt)
    if not _is_admin_by_telegram_id(data_from_jwt['telegram_id']):
        return Response("Forbidden", status=403)

    action = request.form.get('action', '').strip()
    user_id_raw = request.form.get('user_id', '').strip()
    redirect_query = request.form.get('q', '').strip()
    month_count_raw = request.form.get('month_count', '').strip()

    if action not in {"toggle", "extend", "reduce", "change_server", "change_protocol"}:
        return Response("Invalid action", status=400)
    if not user_id_raw:
        return Response("user_id is required", status=400)

    try:
        user_id = int(user_id_raw)
    except ValueError:
        return Response("Invalid user_id", status=400)

    with UsersRepository() as users_repo:
        target_user: User | None = users_repo.get_by_telegram_id(user_id)
    if not target_user:
        return Response("User not found", status=404)

    user_control = UserControl(user_id)
    if action == "toggle":
        if target_user.action:
            user_control.delete()
        else:
            user_control.add(target_user.server_id)
    elif action == "extend":
        if not month_count_raw:
            return Response("month_count is required", status=400)
        try:
            month_count = int(month_count_raw)
        except ValueError:
            return Response("Invalid month_count", status=400)
        if month_count < 1:
            return Response("month_count must be greater than 0", status=400)
        user_control.prolongation(month_count * 30)
    elif action == "reduce":
        if not month_count_raw:
            return Response("month_count is required", status=400)
        try:
            month_count = int(month_count_raw)
        except ValueError:
            return Response("Invalid month_count", status=400)
        if month_count < 1:
            return Response("month_count must be greater than 0", status=400)
        user_control.reduce_subscription(month_count * 30)
    elif action == "change_server":
        server_id_raw = request.form.get('server_id', '').strip()
        if not server_id_raw:
            return Response("server_id is required", status=400)
        try:
            server_id = int(server_id_raw)
        except ValueError:
            return Response("Invalid server_id", status=400)
        with ServersRepository() as servers_repo:
            target_server = servers_repo.get_by_id(server_id)
        if not target_server:
            return Response("Server not found", status=404)
        user_control.update_server(server_id)
    elif action == "change_protocol":
        protocol_raw = request.form.get('protocol', '').strip()
        try:
            protocol_value = int(protocol_raw)
        except ValueError:
            return Response("Invalid protocol", status=400)
        protocol_map = {
            Protocols.xray.value: Protocols.xray,
            Protocols.amneziawg.value: Protocols.amneziawg
        }
        selected_protocol = protocol_map.get(protocol_value)
        if not selected_protocol:
            return Response("Protocol not found", status=404)
        user_control.update_protocol(selected_protocol)

    redirect_url = f"/admin?token={raw_jwt}"
    if redirect_query:
        redirect_url = f"{redirect_url}&q={redirect_query}"
    return redirect(redirect_url)


@admin_panel_bp.route('/logs/download')
def download_logs() -> Response:
    raw_jwt = _read_token_from_request()
    if not raw_jwt:
        return Response("Token is required", status=400)

    data_from_jwt = _decode_token(raw_jwt)
    if not _is_admin_by_telegram_id(data_from_jwt['telegram_id']):
        return Response("Forbidden", status=403)

    if not _LOG_FILE_PATH.exists():
        return Response("Log file not found", status=404)

    return send_file(
        _LOG_FILE_PATH,
        as_attachment=True,
        download_name="logs.txt",
        mimetype="text/plain"
    )
