from ..common import BaseRepository

from db.models import UserToSubscription

from sqlalchemy import select, delete, insert


class UserToSubscriptionRepository(BaseRepository[UserToSubscription]):

    def __init__(self) -> None:
        super().__init__(UserToSubscription)

    def get_by_telegram_id(self, telegram_id: int) -> list[UserToSubscription]:
        """
            Возвращает все строки подписок пользователя.
        """
        query = (
            select(UserToSubscription)
            .where(UserToSubscription.telegram_id == telegram_id)
            .order_by(UserToSubscription.server_id.asc())
        )
        return self.session.execute(query).scalars().all()

    def get_telegram_ids_by_server_id(self, server_id: int) -> list[int]:
        """
            Возвращает telegram_id пользователей, привязанных к серверу
            через user_to_subscription.
        """
        query = select(UserToSubscription.telegram_id).where(
            UserToSubscription.server_id == server_id
        )
        return self.session.execute(query).scalars().all()

    def replace_for_telegram_id(
        self,
        telegram_id: int,
        server_links: dict[int, str]
    ) -> None:
        """
            Заменяет набор подписок пользователя на переданные серверы.
        """
        if not server_links:
            raise ValueError("server_links must not be empty")

        self.session.execute(
            delete(UserToSubscription).where(
                UserToSubscription.telegram_id == telegram_id
            )
        )
        for server_id, server_link in server_links.items():
            self.session.execute(
                insert(UserToSubscription).values(
                    telegram_id=telegram_id,
                    server_id=int(server_id),
                    server_link=server_link
                )
            )
