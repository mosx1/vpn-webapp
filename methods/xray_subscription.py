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


def _is_proxy_outbound(outbound: dict) -> bool:
    protocol = str(outbound.get("protocol") or "").lower()
    tag = str(outbound.get("tag") or "")
    if protocol in _PROXY_PROTOCOLS:
        return True
    return tag == "proxy" or tag.startswith(_PROXY_TAG_PREFIX)


def _split_outbounds(config: dict) -> tuple[list[dict], list[dict]]:
    outbounds = list(config.get("outbounds") or [])
    proxies = [outbound for outbound in outbounds if _is_proxy_outbound(outbound)]
    others = [outbound for outbound in outbounds if not _is_proxy_outbound(outbound)]
    if not proxies and outbounds:
        return [outbounds[0]], outbounds[1:]
    return proxies, others


def merge_xray_client_configs(server_configs: list[tuple[int, dict]]) -> dict[str, Any]:
    """
        Собирает один клиентский JSON из конфигов нескольких серверов.

        Каждый proxy-outbound получает тег proxy-<server_id>, а маршрутизация
        идет через balancer xray-ядра (leastPing + observatory).
    """
    if not server_configs:
        raise ValueError("server_configs must not be empty")

    if len(server_configs) == 1:
        return copy.deepcopy(server_configs[0][1])

    base_server_id, base_config = server_configs[0]
    merged = copy.deepcopy(base_config)
    _base_proxies, base_others = _split_outbounds(merged)

    proxy_outbounds: list[dict] = []
    for server_id, config in server_configs:
        proxies, _others = _split_outbounds(config)
        if not proxies:
            continue
        proxy = copy.deepcopy(proxies[0])
        proxy["tag"] = f"{_PROXY_TAG_PREFIX}{int(server_id)}"
        proxy_outbounds.append(proxy)

    if not proxy_outbounds:
        return merged

    merged["outbounds"] = proxy_outbounds + copy.deepcopy(base_others)

    routing = merged.setdefault("routing", {})
    routing["balancers"] = [
        balancer
        for balancer in (routing.get("balancers") or [])
        if balancer.get("tag") != _BALANCER_TAG
    ]
    selector_tags = [outbound["tag"] for outbound in proxy_outbounds]
    routing["balancers"].append(
        {
            "tag": _BALANCER_TAG,
            "selector": [_PROXY_TAG_PREFIX],
            "fallbackTag": f"{_PROXY_TAG_PREFIX}{int(base_server_id)}",
            "strategy": {"type": "leastPing"},
        }
    )

    rules = list(routing.get("rules") or [])
    replaced_existing_rule = False
    for rule in rules:
        outbound_tag = rule.get("outboundTag")
        if outbound_tag in {"proxy", *selector_tags} or str(outbound_tag).startswith(_PROXY_TAG_PREFIX):
            rule.pop("outboundTag", None)
            rule["balancerTag"] = _BALANCER_TAG
            replaced_existing_rule = True
    if not replaced_existing_rule:
        rules.append(
            {
                "type": "field",
                "network": "tcp,udp",
                "balancerTag": _BALANCER_TAG,
            }
        )
    routing["rules"] = rules

    merged["observatory"] = {
        "subjectSelector": [_PROXY_TAG_PREFIX],
        "probeUrl": "https://www.gstatic.com/generate_204",
        "probeInterval": "2s",
        "enableConcurrency": True,
    }
    return merged


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
    test = [i[1]for i in json_rows]
    if len(json_rows) >= 2:
        return json.dumps(test)#json.dumps(merge_xray_client_configs(json_rows), ensure_ascii=False)

    if json_rows:
        return json.dumps(json_rows[0][1], ensure_ascii=False)

    string_links = [parsed for _server_id, parsed in parsed_rows if isinstance(parsed, str)]
    return "\n".join(string_links)
