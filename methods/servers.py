from methods.common import bool_in_circle_for_text

from db.repository.servers import ServersRepository


def get_info_all_servers() -> list[str]:
    with ServersRepository() as servers_repo:
        info_all_servers = servers_repo.get_info_all_servers()
        message_text: list[str] = [f"{info_all_servers.count} | {info_all_servers.count_pay} : Всего активных"]

        for item in servers_repo.get_info_servers():
            message_text.append(f"{bool_in_circle_for_text(item.answers)}|{item.count}|{item.count_pay}|{item.load}%: {item.name}")
        return message_text