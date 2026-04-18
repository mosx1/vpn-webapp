import requests
from requests.auth import HTTPBasicAuth
from requests import Response

from methods.interfaces import UserControlBase

from db.repository.servers import ServersRepository
from db.models import ServersTable

from config_loader import read_config

_amnezia_cfg = read_config()


class UserControlAmneziaWG(UserControlBase):

    auth = HTTPBasicAuth(
        _amnezia_cfg["AmneziaWG"].get("login"),
        _amnezia_cfg["AmneziaWG"].get("password"),
    )

    @classmethod
    def get_server_id(cls, server_url: str) -> str:
        """
            Не смотря на то что используемое мной api может отдавать несколько серверов, я использую только 1, потому что
            не вижу смысла в использовании нескольких.
        """
        response: Response = requests.get(
            f"http://{server_url}:8084/api/servers",
            auth=cls.auth
        )
        
        res_data = response.json()
        
        return res_data[0]["id"]


    @classmethod
    def add(cls, user_id: int, server_id: int) -> str | None:
        
        with ServersRepository() as server_repo:
               _server: ServersTable | None = server_repo.get_by_id(server_id)
        server_url: str = str(_server.links).split(':')[0]
        if server_url.startswith('http'):
            server_url = server_url.split('://')[1]
        amnezia_server_id: str = cls.get_server_id(server_url)
        response: Response = requests.post(
            f"http://{server_url}:8084/api/servers/{amnezia_server_id}/clients",
            json={
                "name": str(user_id)
            },
            auth=cls.auth
        )
        
        data_new_user = response.json()
        return data_new_user["config"]

    @classmethod
    def delete(cls, user_ids: set[int], server_id: int):
        users_ids_str = [str(user_id) for user_id in user_ids]
        with ServersRepository() as server_repo:
               _server: ServersTable | None = server_repo.get_by_id(server_id)
        server_url: str = str(_server.links).split(':')[0]
        amnezia_server_id: str = cls.get_server_id(server_url)
        response: Response = requests.get(
            f"http://{server_url}:8084/api/servers/{amnezia_server_id}/clients",
            auth=cls.auth
        )
        users: list = response.json()
        for user in users:
            if user["name"] in users_ids_str:
                requests.delete(
                    f"http://{server_url}:8084/api/servers/{amnezia_server_id}/clients/{user["id"]}"
                )
        