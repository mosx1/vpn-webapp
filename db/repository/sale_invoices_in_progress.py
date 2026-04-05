from ..common import BaseRepository

from db.models import SaleInvoicesInProgress

from sqlalchemy import insert


class SaleInvoicesInProgressRepository(BaseRepository[SaleInvoicesInProgress]):
    
    def __init__(self):
        super().__init__(SaleInvoicesInProgress)

    def add_sale_invoice(self, label: str, user_id: int, server_id: int, month_count: int) -> None:

        query = insert(SaleInvoicesInProgress).values(
            telegram_id=user_id,
            label=label,
            server_id=server_id,
            month_count=month_count
        )
        self.session.execute(query)
        self.session.commit()  