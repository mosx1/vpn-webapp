import time

from methods.servers import check_answers_servers

def health_check_task():
    while True:
        check_answers_servers()
        time.sleep(60)

# def backup_server_config_task():
#     servers = get_server_list()
#     while True:
#         for server in servers:
#             run_backup_server_config(server.links)
#         time.sleep(60 * 60)