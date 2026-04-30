from flask import Blueprint, request, jsonify, Response

from connect import logging


payment_bp = Blueprint('payment_bp', __name__, url_prefix='/payment')



@payment_bp.route('/info', methods=['POST'])
def payment_info() -> Response:
    payload = request.get_json(silent=True) or {}
    label = str(payload.get('label') or request.form.get('label') or '').strip()
    logging.info(f"Payment info: {payload}")
    return jsonify({"status": "success"}), 200
