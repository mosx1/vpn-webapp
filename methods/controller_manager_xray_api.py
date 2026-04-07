from db.models import ServersTable
import requests, json

from connect import logging

from db.repository.servers import ServersRepository
from db.repository.security import SecurityRepository
from methods.interfaces import UserControlBase

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

          response = requests.get(
               "http://{}/add?user_id={}&token={}".format(
                    server.links,
                    user_id,
                    token
               ),
               timeout=60
          )

          response = response.json()
          if response["success"]:
               return response["link"]

          logging.error("Ошибка в запросе на добавление пользователя")



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
          response = requests.post(
               "http://{}/del".format(
                    server.links
               ),
               data = json.dumps(data),
               timeout=60
               ).json()

          return str(response)


