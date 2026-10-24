import copy
import json
from typing import Any


_PROXY_PROTOCOLS = {"vless", "vmess", "trojan", "shadowsocks"}
_BALANCER_TAG = "balancer"
_PROXY_TAG_PREFIX = "proxy-"


def _parse_server_link(server_link: str | dict | None) -> dict | str | None:
    if server_link is None:
        return None
    if isinstance(server_link, dict):
        return server_link
    raw_link = str(server_link).strip()
    if not raw_link:
        return None
    if raw_link.startswith("vless://"):
        return raw_link
    try:
        parsed = json.loads(raw_link)
    except json.JSONDecodeError:
        return raw_link
    if isinstance(parsed, dict):
        return parsed
    return raw_link


def build_subscription_payload(server_rows: list[tuple[int, str]]) -> str:
    """
        Собирает тело подписки из строк user_to_subscription.

        Одна запись — как раньше, исходный server_link.
        Несколько JSON-конфигов — один outbound-конфиг с balancer.
        Несколько vless:// — список ссылок, по одной на строку.
    """
    if not server_rows:
        return ""
    if len(server_rows) == 1:
        return str(server_rows[0][1] or "")

    parsed_rows: list[tuple[int, dict | str]] = []
    for server_id, server_link in server_rows:
        parsed = _parse_server_link(server_link)
        if parsed is None:
            continue
        parsed_rows.append((int(server_id), parsed))

    json_rows = [
        (server_id, parsed)
        for server_id, parsed in parsed_rows
        if isinstance(parsed, dict)
    ]
    json_configs = [i[1]for i in json_rows]
    if len(json_rows) >= 2:
        return json.dumps(json_configs)

    if json_rows:
        return json.dumps(json_rows[0][1], ensure_ascii=False)

    string_links = [parsed for _server_id, parsed in parsed_rows if isinstance(parsed, str)]
    return "\n".join(string_links)
