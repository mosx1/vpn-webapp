import json
import uuid
from urllib.parse import quote, urlencode, urlparse

import requests
from requests import Response, Session

from connect import logging
from config_loader import read_config
from db.models import ServersTable
from db.repository.servers import ServersRepository
from methods.interfaces import UserControlBase


class UserControl3xUI(UserControlBase):
    @staticmethod
    def _safe_json(value: str | dict | None) -> dict:
        if not value:
            return {}
        if isinstance(value, dict):
            return value
        return json.loads(value)

    @classmethod
    def _build_vless_json_link(cls, server_link: str, inbound_obj: dict, client: dict, settings: dict) -> str:
        parsed = urlparse(server_link)
        host = parsed.hostname or parsed.path.split("/")[0]
        if not host:
            raise RuntimeError(f"Cannot determine host from server link: {server_link}")

        port = inbound_obj.get("port")
        if not port:
            raise RuntimeError("Inbound port is missing in 3x-ui response")

        client_id = client.get("id")
        if not client_id:
            raise RuntimeError("Client id is missing for VLESS link generation")

        remark = inbound_obj.get("remark") or f"user-{client.get('email', '')}"
        stream = cls._safe_json(inbound_obj.get("streamSettings"))

        query: dict[str, str] = {
            "type": stream.get("network", "tcp"),
            "security": stream.get("security", "none"),
        }
        xhttp_settings = cls._safe_json(stream['xhttpSettings'])
        query['host'] = xhttp_settings.get('host')
        query['mode'] = xhttp_settings.get('mode')
        query['encryption'] = settings.get('encryption')

        stream_reality_settings_settings = stream.get('realitySettings').get('settings')
        query['pbk'] = stream_reality_settings_settings.get('publicKey')
        query['spx'] = stream_reality_settings_settings.get('spiderX')
        query['pqv'] = stream_reality_settings_settings.get('mldsa65Verify')
        network = query["type"]
        if network == "ws":
            ws_settings = cls._safe_json(stream.get("wsSettings"))
            ws_headers = cls._safe_json(ws_settings.get("headers"))
            if ws_settings.get("path"):
                query["path"] = ws_settings["path"]
            if ws_headers.get("Host"):
                query["host"] = ws_headers["Host"]
        elif network == "grpc":
            grpc_settings = cls._safe_json(stream.get("grpcSettings"))
            if grpc_settings.get("serviceName"):
                query["serviceName"] = grpc_settings["serviceName"]

        security = query["security"]
        if security == "tls":
            tls_settings = cls._safe_json(stream.get("tlsSettings"))
            if tls_settings.get("serverName"):
                query["sni"] = tls_settings["serverName"]
            alpn = tls_settings.get("alpn") or []
            if isinstance(alpn, list) and alpn:
                query["alpn"] = ",".join(alpn)
            if tls_settings.get("fingerprint"):
                query["fp"] = tls_settings["fingerprint"]
        elif security == "reality":
            reality_settings = cls._safe_json(stream.get("realitySettings"))
            if reality_settings.get("serverNames"):
                server_names = reality_settings["serverNames"]
                if isinstance(server_names, list) and server_names:
                    query["sni"] = server_names[0]
            if reality_settings.get("fingerprint"):
                query["fp"] = reality_settings["fingerprint"]
            if reality_settings.get("shortIds"):
                short_ids = reality_settings["shortIds"]
                if isinstance(short_ids, list) and short_ids and short_ids[0]:
                    query["sid"] = short_ids[0]


        return {
            "log": {},
            "remarks": f"Выгодный ВПН - {query["host"]}",
            "inbounds": [
                {
                    "settings": {
                        "udp": True,
                        "userLevel": 8,
                        "auth": "noauth",
                    },
                    "listen": "127.0.0.1",
                    "port": 10808,
                    "tag": "socks",
                    "protocol": "socks",
                },
                {
                    "settings": {
                        "userLevel": 8,
                        "udp": True,
                        "auth": "noauth",
                    },
                    "listen": "127.0.0.1",
                    "port": 1087,
                    "tag": "directSocks",
                    "protocol": "socks",
                },
                {
                    "settings": {
                        "address": "[::1]",
                    },
                    "listen": "[::1]",
                    "port": 62789,
                    "tag": "api",
                    "protocol": "dokodemo-door",
                },
            ],
            "outbounds": [
                {
                    "tag": "proxy",
                    "protocol": "vless",
                    "streamSettings": {
                        "sockopt": {
                            "dialerProxy": "fragment",
                            "tcpNoDelay": True,
                        },
                        "network": "tcp",
                        "security": "reality",
                        "tcpSettings": {
                            "header": {
                                "type": "none",
                            },
                        },
                        "realitySettings": {
                            "publicKey": query['pbk'],
                            "serverName": query["sni"],
                            "show": False,
                            "mldsa65Verify": "",
                            "spiderX": "",
                            "shortId": query["sid"],
                            "fingerprint": "firefox",
                        },
                    },
                    "settings": {
                        "vnext": [
                            {
                                "port": port,
                                "users": [
                                    {
                                        "encryption": "none",
                                        "flow": "xtls-rprx-vision",
                                        "id": client_id,
                                        "level": 8,
                                        "email": "",
                                    },
                                ],
                                "address": host,
                            },
                        ],
                    },
                    "mux": {
                        "concurrency": 50,
                        "xudpConcurrency": 128,
                        "xudpProxyUDP443": "allow",
                        "enabled": False,
                    },
                },
                {
                    "settings": {
                        "userLevel": 8,
                        "fragment": {
                            "length": "80-250",
                            "interval": "10-100",
                            "packets": "tlshello",
                        },
                    },
                    "streamSettings": {
                        "sockopt": {
                            "tcpNoDelay": True,
                        },
                    },
                    "tag": "fragment",
                    "protocol": "freedom",
                },
            ],
            "api": {
                "tag": "api",
                "services": [
                    "StatsService",
                ],
            },
            "dns": {
                "queryStrategy": "UseIP",
                "servers": [
                    {
                        "address": "8.8.8.8",
                        "skipFallback": False,
                    },
                ],
                "tag": "dnsQuery",
                "disableCache": True,
                "disableFallbackIfMatch": True,
                "hosts": {
                    "dns.quad9.net": [
                        "9.9.9.9",
                        "149.112.112.112",
                        "2620:fe::fe",
                        "2620:fe::9",
                    ],
                    "one.one.one.one": [
                        "1.1.1.1",
                        "1.0.0.1",
                        "2606:4700:4700::1111",
                        "2606:4700:4700::1001",
                    ],
                    "dns.google": [
                        "8.8.8.8",
                        "8.8.4.4",
                        "2001:4860:4860::8888",
                        "2001:4860:4860::8844",
                    ],
                    "cloudflare-dns.com": [
                        "104.16.248.249",
                        "104.16.249.249",
                        "2606:4700::6810:f8f9",
                        "2606:4700::6810:f9f9",
                    ],
                    "dns.alidns.com": [
                        "223.5.5.5",
                        "223.6.6.6",
                        "2400:3200::1",
                        "2400:3200:baba::1",
                    ],
                    "dns.cloudflare.com": [
                        "104.16.132.229",
                        "104.16.133.229",
                        "2606:4700::6810:84e5",
                        "2606:4700::6810:85e5",
                    ],
                    "common.dot.dns.yandex.net": [
                        "77.88.8.8",
                        "77.88.8.1",
                        "2a02:6b8::feed:0ff",
                        "2a02:6b8:0:1::feed:0ff",
                    ],
                    "dot.pub": [
                        "1.12.12.12",
                        "120.53.53.53",
                    ],
                },
                "disableFallback": True,
            },
            "stats": {},
            "routing": {
                "balancers": [],
                "domainStrategy": "AsIs",
                "rules": [
                    {
                        "type": "field",
                        "outboundTag": "direct",
                        "domain": [
                            "geosite:private",
                            "geosite:apple",
                        ],
                        "ruleTag": "rule-0",
                    },
                    {
                        "type": "field",
                        "inboundTag": [
                            "api",
                        ],
                        "outboundTag": "api",
                        "ruleTag": "rule-1",
                    },
                    {
                        "type": "field",
                        "inboundTag": [
                            "dnsQuery",
                        ],
                        "outboundTag": "proxy",
                        "ruleTag": "rule-2",
                    },
                    {
                        "type": "field",
                        "inboundTag": [
                            "directSocks",
                        ],
                        "outboundTag": "direct",
                        "ruleTag": "rule-3",
                    },
                    {
                        "type": "field",
                        "outboundTag": "direct",
                        "domain": [
                            "geosite:private",
                            "geosite:apple",
                        ],
                        "ruleTag": "rule-4",
                    },
                    {
                        "type": "field",
                        "inboundTag": [
                            "api",
                        ],
                        "outboundTag": "api",
                        "ruleTag": "rule-5",
                    },
                    {
                        "type": "field",
                        "inboundTag": [
                            "dnsQuery",
                        ],
                        "outboundTag": "proxy",
                        "ruleTag": "rule-6",
                    },
                    {
                        "type": "field",
                        "inboundTag": [
                            "directSocks",
                        ],
                        "outboundTag": "direct",
                        "ruleTag": "rule-7",
                    },
                ],
            },
            "policy": {
                "system": {
                    "statsOutboundDownlink": True,
                    "statsInboundUplink": True,
                    "statsOutboundUplink": True,
                    "statsInboundDownlink": True,
                },
                "levels": {
                    "8": {
                        "statsUserUplink": False,
                        "handshake": 4,
                        "connIdle": 30,
                        "uplinkOnly": 1,
                        "bufferSize": 0,
                        "statsUserDownlink": False,
                        "downlinkOnly": 1,
                    },
                },
            },
            "transport": {},
        }
        # preserve key order for readability in clients
        query_string = urlencode(list(query.items()), doseq=False)
        return f"vless://{client_id}@{host}:{port}?{query_string}#{quote(str(remark))}"

    @classmethod
    def _get_server(cls, server_id: int) -> ServersTable:
        with ServersRepository() as server_repo:
            server: ServersTable | None = server_repo.get_by_id(server_id)
        if not server:
            raise RuntimeError(f"Server with id={server_id} not found")
        return server

    @classmethod
    def _get_3xui_config(cls) -> dict[str, str]:
        cfg = read_config()
        section_name = "3xUI"
        if not cfg.has_section(section_name):
            raise RuntimeError("Config section [3xUI] is required for 3x-ui strategy")
        section = cfg[section_name]
        return {
            "username": section.get("username", "").strip(),
            "password": section.get("password", "").strip(),
            "inbound_id": section.getint("inbound_id", 2),
            "subscription_template": section.get("subscription_template", "").strip(),
            "client_id_field": section.get("client_id_field", "id").strip(),
        }

    @classmethod
    def _login(cls, base_url: str, username: str, password: str) -> Session:
        if not username or not password:
            raise RuntimeError("3x-ui username/password are not configured")
        session = requests.Session()
        session.verify = False
        response: Response = session.post(
            f"{base_url}/login",
            json={"username": username, "password": password},
            timeout=20
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success", False):
            raise RuntimeError(f"3x-ui login failed: {payload}")
        return session

    @classmethod
    def _extract_clients(cls, inbound_payload: dict) -> list[dict]:
        obj = inbound_payload.get("obj") or {}
        settings_raw = obj.get("settings") or "{}"
        if isinstance(settings_raw, str):
            settings = json.loads(settings_raw)
        else:
            settings = settings_raw
        return settings.get("clients", [])

    @classmethod
    def add(cls, user_id: int, server_id: int) -> str | None:
        server = cls._get_server(server_id)
        config = cls._get_3xui_config()
        inbound_id = int(config["inbound_id"])
        session = cls._login(server.links, config["username"], config["password"])
        client_uuid = str(uuid.uuid4())
        sub_id = uuid.uuid4().hex[:16]
        client = {
            "id": client_uuid,
            "email": str(user_id),
            "enable": True,
            "subId": sub_id,
        }
        payload = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client]}, ensure_ascii=False),
        }
        
        response: Response = session.post(
            f"{server.links}/panel/api/inbounds/addClient",
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success", False):
            logging.error("3x-ui addClient failed: %s", data)

        inbound_resp: Response = session.get(
            f"{server.links}/panel/api/inbounds/get/{inbound_id}",
            timeout=20,
        )
        inbound_resp.raise_for_status()
        inbound_data = inbound_resp.json()
        if not inbound_data.get("success", False):
            raise RuntimeError(f"3x-ui get inbound failed: {inbound_data}")

        inbound_obj = inbound_data.get("obj") or {}
        protocol = str(inbound_obj.get("protocol", "")).lower()
        if protocol != "vless":
            raise RuntimeError(
                f"Expected VLESS inbound, got protocol={protocol!r}. "
                "Set [3xUI].inbound_id to a VLESS inbound."
            )

        settings = cls._safe_json(inbound_obj.get("settings"))
        matched_client = None
        for item in settings.get("clients", []):
            if item.get("email") == str(user_id):
                matched_client = item
                break
        if not matched_client:
            matched_client = client
        
        subscription_link = cls._build_vless_json_link(server.links, inbound_obj, matched_client, settings)
        logging.info("3x-ui client %s added to inbound %s", user_id, inbound_id)
        return subscription_link

    @classmethod
    def delete(cls, user_ids: set[int], server_id: int) -> None:
        if not user_ids:
            return

        server = cls._get_server(server_id)
        config = cls._get_3xui_config()
        inbound_id = int(config["inbound_id"])
        client_id_field = config["client_id_field"] or "id"

        session = cls._login(server.links, config["username"], config["password"])
        inbound_resp: Response = session.get(
            f"{server.links}/panel/api/inbounds/get/{inbound_id}",
            timeout=20,
        )
        inbound_resp.raise_for_status()
        inbound_data = inbound_resp.json()
        if not inbound_data.get("success", False):
            raise RuntimeError(f"3x-ui get inbound failed: {inbound_data}")
        clients = cls._extract_clients(inbound_data)

        users_to_delete = {str(user_id) for user_id in user_ids}
        for client in clients:
            if client.get("email") not in users_to_delete:
                continue
            client_id = client.get(client_id_field) or client.get("id")
            if not client_id:
                logging.warning(
                    "3x-ui client id missing for user email %s",
                    client.get("email"),
                )
                continue
            
            del_resp: Response = session.post(
                f"{server.links}/panel/api/inbounds/{inbound_id}/delClient/{client_id}",
                timeout=20,
            )
            del_resp.raise_for_status()
            del_data = del_resp.json()
            if not del_data.get("success", False):
                raise RuntimeError(f"3x-ui delClient failed: {del_data}")
            logging.info("3x-ui client %s removed from inbound %s", client["email"], inbound_id)
