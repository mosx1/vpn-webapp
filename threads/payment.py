# import time

# from db.models import SaleInvoicesInProgress

# from methods.payment.yoomoneyMethods import getInfoLastPayment

# from configparser import ConfigParser

# from db.repository.sale_invoices_in_progress import SaleInvoicesInProgressRepository


# def check_payments() -> None:

#     config = ConfigParser()
#     config.read('config.ini')

#     while True:

#         with SaleInvoicesInProgressRepository() as siip_repo:

#             invoices = siip_repo.get_sale_invoice_by_label()
            
#         for invoice_item in invoices:
            
#             invoice: SaleInvoicesInProgress = invoice_item[0]
#             stop_date_time = invoice_item[1]
#             current_date_time = invoice_item[2]

#             try:
#                 info_last_payment: dict | None = getInfoLastPayment(invoice.label)
#             except Exception as e:
#                 print(str(e))
#                 continue
            
#             if not invoice.is_gift and info_last_payment and invoice.server_id:
#                 success_payment(invoice)
#             if invoice.is_gift and info_last_payment:
#                 success_payment_gift(invoice)

#             if current_date_time.strftime("%Y-%m-%d %H:%M:%S") > stop_date_time.strftime("%Y-%m-%d %H:%M:%S"):
#                 delete_invoice(invoice)
#         time.sleep(10)