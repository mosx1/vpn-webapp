import requests

from flask import Blueprint, request, jsonify, Response

from connect import logging
from config_loader import read_config
from methods.payment.yoomoneyMethods import getInfoLastPayment


payment_bp = Blueprint('payment_bp', __name__, url_prefix='/payment')


def _send_payment_info_to_telegram(message: str, chat_id: int = 474425142) -> tuple[bool, str]:
    config = read_config()
    if not config.has_section('TelegramBot'):
        return False, "TelegramBot section not found in config"

    bot_token = "6147861985:AAGAyD37AZMgXJIfI-8KBkZpjzZ_Kvmi-QI"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message
            },
            timeout=10
        )
    except requests.RequestException as error:
        logging.exception("Failed to send payment info to telegram: %s", error)
        return False, "Telegram API request failed"

    if not response.ok:
        logging.error(
            "Telegram sendMessage failed. status=%s, body=%s",
            response.status_code,
            response.text
        )
        return False, f"Telegram API returned {response.status_code}"

    return True, "Sent"


@payment_bp.route('/info', methods=['POST'])
def payment_info() -> Response:
    payload = request.get_json(silent=True) or {}
    label = str(payload.get('label') or request.form.get('label') or '').strip()
    _send_payment_info_to_telegram(str(payload))
    if not label:
        return jsonify({"error": "label is required"}), 400

    try:
        info_last_payment: dict | None = getInfoLastPayment(label)
    except Exception as error:
        logging.exception("Failed to fetch payment info for label %s: %s", label, error)
        return jsonify({"error": "Failed to fetch payment info"}), 502

    if not info_last_payment:
        return jsonify({"status": "not_found", "message": "Payment not found"}), 404

    return jsonify(info_last_payment), 200
