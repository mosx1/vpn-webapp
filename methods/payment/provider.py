from config_loader import read_config
from methods.payment.yoomoneyMethods import get_link_payment as get_yoomoney_link_payment
from methods.payment.trybit import get_link_payment as get_trybit_link_payment


def _payment_provider() -> str:
    conf = read_config()
    if not conf.has_section("Payment"):
        return "yoomoney"
    return conf["Payment"].get("provider", "yoomoney").strip().lower()


def is_trybit_configured() -> bool:
    conf = read_config()
    if not conf.has_section("Trybit"):
        return False
    shop_id = conf["Trybit"].get("shop_id", "").strip()
    api_key = conf["Trybit"].get("api_key", "").strip()
    return bool(shop_id and api_key)


def get_link_payment(label: str, month: int, provider: str | None = None) -> str:
    selected = (provider or _payment_provider()).strip().lower()
    if selected in ("trybit", "crypto"):
        return get_trybit_link_payment(label, month)
    return get_yoomoney_link_payment(label, month)
