import json

from typing import Any, List

from flask import Blueprint, Response, request, jsonify

from db.models import User
from db.repository.users import UsersRepository

from core.security import is_valid_security_key


vpn_app_bp = Blueprint('vpn_app', __name__, url_prefix='/my_app')


@vpn_app_bp.before_request
def _() -> Response | None:
    if not is_valid_security_key(request.args.get('token')):
        return jsonify(
            {
                "success": False
            }
        )
            

@vpn_app_bp.route('/list_users')
def get_users() -> dict[str, Any]:
    """
    Return users list for external app.
    ---
    tags:
      - Mobile App
    parameters:
      - in: query
        name: token
        required: true
        type: string
        description: Security token for service access.
      - in: query
        name: limit
        required: false
        type: integer
      - in: query
        name: offset
        required: false
        type: integer
    responses:
      200:
        description: Array of users with telegram_id, name and action.
      401:
        description: Invalid security token.
    """

    with UsersRepository() as repo:

        print(
            "TEST",
            repo.get_all(
            request.args.get('limit', type=int),
            request.args.get('offset', type=int)
        ))

        users: List[User]  = repo.get_all(
            request.args.get('limit', type=int),
            request.args.get('offset', type=int)
        )

        return Response(
            json.dumps(
                [
                    {
                        "telegram_id": user.telegram_id,
                        "name": user.name,
                        "action": user.action
                    } for user in users
                ],
                ensure_ascii=False
            ),
            mimetype='application/json; charset=utf-8'
        )