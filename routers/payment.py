import requests

from flask import Blueprint, request, jsonify, Response

from connect import logging
from config_loader import read_config
from methods.payment.yoomoneyMethods import getInfoLastPayment


payment_bp = Blueprint('payment_bp', __name__, url_prefix='/payment')


def _send_payment_info_to_telegram(message: str):

    bot_token = "6147861985:AAGlUZN2W5cGkOisXlEiY2-H8yZhwgNQ2Rk"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    requests.post(
        url,
        json={
            "chat_id": "474425142",
            "text": message
        },
        timeout=10
    )


@payment_bp.route('/info', methods=['POST'])
def payment_info() -> Response:
    payload = request.get_json(silent=True) or {}
    label = str(payload.get('label') or request.form.get('label') or '').strip()
    _send_payment_info_to_telegram(str(payload))
    return jsonify({"status": "success"}), 200
