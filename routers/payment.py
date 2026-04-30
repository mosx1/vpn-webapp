from flask import Blueprint, request, jsonify, Response

from db.repository.sale_invoices_in_progress import SaleInvoicesInProgressRepository
from db.models import SaleInvoicesInProgress

from connect import logging


payment_bp = Blueprint('payment_bp', __name__, url_prefix='/payment')

@payment_bp.route('/info', methods=['POST'])
def payment_info() -> Response:
    payload = request.get_json(silent=True) or {}
    label = str(payload.get('label') or request.form.get('label') or '').strip()
    with SaleInvoicesInProgressRepository() as siip_repo:
        invoice: SaleInvoicesInProgress | None = siip_repo.get_one(SaleInvoicesInProgress.label == label)

    if not invoice:
        return jsonify({"error": "label is required"}), 400
    logging.info(f"Найден платеж: {invoice.id}")
    return jsonify("success"), 200