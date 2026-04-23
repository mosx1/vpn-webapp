from ..common import BaseRepository

from db.models import SaleInvoicesInProgress

from sqlalchemy import insert, select, func, text


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

    def get_sale_invoice_by_label(self) -> SaleInvoicesInProgress | None:
        query = select(
            SaleInvoicesInProgress, 
            (SaleInvoicesInProgress.create_date + text("INTERVAL '1 hour'")).label("stop_date_time"),
            func.now().label("current_date_time")
        )
        result = self.session.execute(query)
        return result.fetchall()