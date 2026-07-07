from db.models import ServersTable
import json

import requests
from requests import Response

from connect import logging

from db.repository.servers import ServersRepository
from db.repository.security import SecurityRepository
from methods.interfaces import UserControlBase


def _parse_xray_response(response: Response, action: str) -> dict | None:
    if not response.text or not response.text.strip():
        logging.warning(
            "Xray %s: empty response from %s (status=%s)",
            action,
            response.url,
            response.status_code,
        )
        return None

    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        body_preview = response.text[:500]
        logging.error(
            "Xray %s: invalid JSON from %s (status=%s): %s",
            action,
            response.url,
            response.status_code,
            body_preview,
        )
        return None

    if not isinstance(payload, dict):
        logging.error(
            "Xray %s: unexpected payload type from %s: %r",
            action,
            response.url,
            payload,
        )
        return None

    return payload


class UserControlXray(UserControlBase):
     
     @staticmethod
     def add(
          user_id: int,
          server: int
     ) -> str | None:
          """
               Создает пользователя в xray
          """

          with ServersRepository() as server_repo:
               
               server: ServersTable | None = server_repo.get_by_id(server)

               if not server:
                    raise 'error'

          with SecurityRepository() as security_repo:
               token: str = security_repo.get()

          logging.info(
               f'Создание пользователя {user_id} на сервере {server.links}'
          )

          http_response = requests.get(
               "http://{}/add?user_id={}&token={}".format(
                    server.links,
                    user_id,
                    token
               ),
               timeout=60
          )

          response = _parse_xray_response(http_response, "add")
          if response and response.get("success"):
               return response["link"]

          logging.error(
               "Ошибка в запросе на добавление пользователя: status=%s body=%s",
               http_response.status_code,
               http_response.text[:500],
          )



     # def suspend_users(
     #      user_ids: set[int],
     #      server: int,
     #      token: str = utils.get_token()
     # ) -> bool | None:
     #      """
     #           Приостонавливает пользователя в xray
     #      """
     #      data = {
     #           "token": token,
     #           "user_ids": list(user_ids)
     #      }
     #      response = requests.post(
     #           "http://{}/suspend".format(
     #                utils.getUrlByIdServer(server)
     #           ),
     #           data = json.dumps(data),
     #           timeout=20
     #           ).json()

     #      if "success" in response and response["success"]:
     #           return response["success"]

     #      if "detail" in response and response["detail"] and response["detail"] == "Method Not Allowed":
               
     #           time.sleep(5)

     #           return suspend_users(
     #                user_ids,
     #                server,
     #                token
     #           )

     #      logging.error("Ошибка в запросе на добавление пользователя")



     # def resume_user(
     #      userId: int,
     #      server: int,
     #      token: str = utils.get_token()     
     # ) -> str | NetworkServiceError:
     #      """
     #           Возобновляет доступ пользователя к xray
     #      """

     #      logging.info(
     #           'Возобновление пользователя ' + str(userId) + ' на сервере ' + utils.getUrlByIdServer(server)
     #      )

     #      response = requests.get(
     #           "http://{}/resume?userId={}&token={}".format(
     #                utils.getUrlByIdServer(server),
     #                userId,
     #                token
     #                ),
     #           timeout=60
     #           ).json()
     #      if response["success"]:
     #           return response["success"]

     #      return NetworkServiceError(
     #           caption="Ошибка в запросе на восстановление пользователя",
     #           response=str(response)
     #      )


     @staticmethod
     def delete(
          user_ids: set[int],
          server: int
     ) -> bool:
          """
               Удаляет пользователей с сервера
          """
          if server in [8, 10]:
               return "skip"
          with ServersRepository() as server_repo:
                    
                    server: ServersTable | None = server_repo.get_by_id(server)

                    if not server:
                         raise 'error'

          with SecurityRepository() as security_repo:
                    token: str = security_repo.get()

          data = {
               "token": token,
               "user_ids": list(user_ids)
          }
          http_response = requests.post(
               "http://{}/del".format(
                    server.links
               ),
               data=json.dumps(data),
               headers={"Content-Type": "application/json"},
               timeout=60
          )

          response = _parse_xray_response(http_response, "delete")
          if response is None:
               logging.warning(
                    "Xray delete: proceeding without parsed response for users %s on server %s",
                    user_ids,
                    server.links,
               )
               return False

          if response.get("success") is False:
               logging.error(
                    "Xray delete failed for users %s on server %s: %s",
                    user_ids,
                    server.links,
                    response,
               )

          return bool(response.get("success", True))


