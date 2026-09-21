"""Проверка приведения адреса панели 3x-ui к абсолютному url."""

import pytest

from methods.controller_3x_ui import UserControl3xUI


@pytest.mark.parametrize(
    "server_link, expected",
    [
        ("1.2.3.4:2053", "http://1.2.3.4:2053"),
        ("panel.example.com:2053", "http://panel.example.com:2053"),
        ("http://panel.example.com:2053", "http://panel.example.com:2053"),
        ("https://panel.example.com:2053", "https://panel.example.com:2053"),
        ("  1.2.3.4:2053/  ", "http://1.2.3.4:2053"),
    ]
)
def test_panel_base_url_adds_scheme(server_link, expected):
    assert UserControl3xUI._panel_base_url(server_link) == expected


def test_panel_base_url_rejects_empty_link():
    with pytest.raises(RuntimeError):
        UserControl3xUI._panel_base_url("")


def test_vless_link_host_has_no_port():
    """Хост в vless-ссылке берется из абсолютного url, порт приходит из inbound."""
    inbound_obj = {
        "port": 443,
        "remark": "test",
        "streamSettings": {
            "network": "tcp",
            "security": "reality",
            "xhttpSettings": {"host": "example.com", "mode": "auto"},
            "realitySettings": {"settings": {"publicKey": "pk", "spiderX": "/", "mldsa65Verify": ""}},
        },
    }
    client = {"id": "uuid-1", "email": "42"}

    link = UserControl3xUI._build_vless_json_link(
        UserControl3xUI._panel_base_url("panel.example.com:2053"),
        inbound_obj,
        client,
        {"encryption": "none"},
    )

    assert link.startswith("vless://uuid-1@panel.example.com:443?")
