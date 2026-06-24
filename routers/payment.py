from flask import Blueprint, request, jsonify, Response

from db.repository.sale_invoices_in_progress import SaleInvoicesInProgressRepository
from db.models import SaleInvoicesInProgress

from methods.payment.common import success_payment, success_payment_gift

payment_bp = Blueprint('payment_bp', __name__, url_prefix='/payment')

@payment_bp.route('/info', methods=['POST'])
def payment_info() -> Response:
    """
    Process successful payment callback by label.
    ---
    tags:
      - Payment
    consumes:
      - application/json
      - application/x-www-form-urlencoded
    parameters:
      - in: body
        name: payload
        required: false
        schema:
          type: object
          properties:
            label:
              type: string
      - in: formData
        name: label
        required: false
        type: string
    responses:
      200:
        description: Payment processed.
      400:
        description: Invalid or missing label.
    """
    payload = request.get_json(silent=True) or {}
    label = str(payload.get('label') or request.form.get('label') or '').strip()
    with SaleInvoicesInProgressRepository() as siip_repo:
        invoice: SaleInvoicesInProgress | None = siip_repo.get_one(SaleInvoicesInProgress.label == label)

    if not invoice:
        return jsonify({"error": "label is required"}), 400

    if invoice.is_gift:
        success_payment_gift(invoice)
    else:
        success_payment(invoice)
    return jsonify("success"), 200