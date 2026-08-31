import requests
from concurrent.futures import ThreadPoolExecutor

from methods.common import bool_in_circle_for_text

from db.repository.servers import ServersRepository
from db.models import ServersTable


def get_info_all_servers() -> list[str]:
    with ServersRepository() as servers_repo:
        info_all_servers = servers_repo.get_info_all_servers()
        message_text: list[str] = [f"{info_all_servers.count} | {info_all_servers.count_pay} : Всего активных"]

        for item in servers_repo.get_info_servers():
            message_text.append(f"{bool_in_circle_for_text(item.answers)}|{item.count}|{item.count_pay}|{item.load}%: {item.name}")
        return message_text

def health_check(url: str) -> int:
    try:
        res = requests.get(url, timeout=5)
        return res.status_code
    except Exception:
        pass

def health_check_and_update_answers(server: ServersTable):
    code = health_check(f"http://{server.links}/config")
    answers = bool(code == 200)
    with ServersRepository() as servers_repo:
        servers_repo.update_answer(server.id, answers)
        servers_repo.session.commit()

def check_answers_servers():
    with ServersRepository() as servers_repo:
        servers: list[ServersTable] = servers_repo.get_server_list()
    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(health_check_and_update_answers, servers))