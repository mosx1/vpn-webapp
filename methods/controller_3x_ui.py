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
    def _build_vless_link(cls, server_link: str, inbound_obj: dict, client: dict, settings: dict) -> str:
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
        
        subscription_link = cls._build_vless_link(server.links, inbound_obj, matched_client, settings)
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
