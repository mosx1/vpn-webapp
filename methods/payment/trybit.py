import requests

from config_loader import read_config
from connect import logging

_TRYBIT_CREATE_INVOICE_URL = "https://api.trybit.com/v2/invoice/create"
_TRYBIT_INVOICE_INFO_URL = "https://api.trybit.com/v2/invoice/merchant/info"


def _get_trybit_headers() -> dict[str, str]:
    conf = read_config()
    api_key = conf["Trybit"].get("api_key", "").strip()
    return {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }


def _get_trybit_shop_id() -> str:
    conf = read_config()
    return conf["Trybit"].get("shop_id", "").strip()


def create_invoice(label: str, month: int) -> dict:
    conf = read_config()
    amount_rub = conf["Price"].getint("RUB") * month
    payload = {
        "shop_id": _get_trybit_shop_id(),
        "amount": amount_rub,
        "currency": "RUB",
        "order_id": label,
    }

    response = requests.post(
        _TRYBIT_CREATE_INVOICE_URL,
        headers=_get_trybit_headers(),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    response_json = response.json()
    if response_json.get("status") != "success" or not response_json.get("result"):
        raise RuntimeError(f"Trybit invoice create failed: {response_json}")
    return response_json["result"]


def get_link_payment(label: str, month: int) -> str:
    result = create_invoice(label, month)
    invoice_link = result.get("link")
    if not invoice_link:
        raise RuntimeError(f"Trybit invoice link is empty: {result}")
    return invoice_link


def get_invoice_info(uuid: str) -> dict | None:
    if not uuid:
        return None

    payload = {"uuids": [uuid]}
    response = requests.post(
        _TRYBIT_INVOICE_INFO_URL,
        headers=_get_trybit_headers(),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    response_json = response.json()
    if response_json.get("status") != "success":
        logging.error("Trybit invoice info failed: %s", response_json)
        return None
    result = response_json.get("result") or []
    if not result:
        return None
    return result[0]


def is_paid_status(invoice_info: dict | None) -> bool:
    if not invoice_info:
        return False
    status = str(invoice_info.get("status") or "").strip().lower()
    invoice_status = str(invoice_info.get("invoice_status") or "").strip().lower()
    return status in {"paid", "overpaid"} or invoice_status == "success"
