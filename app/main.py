import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.config import APP_NAME, MIN_FONT_PX
from app.controllers.order_controller import OrderController
from app.controllers.product_controller import ProductController
from app.controllers.report_controller import ReportController
from app.database.schema import init_schema, seed_sample_products
from app.models.repositories import (
    CustomerRepository,
    InvoiceRepository,
    ProductRepository,
    ReportRepository,
)
from app.views.main_window import MainWindow


def build_controllers() -> tuple[ProductController, OrderController, ReportController]:
    product_repo = ProductRepository()
    customer_repo = CustomerRepository()
    invoice_repo = InvoiceRepository()
    report_repo = ReportRepository()

    product_controller = ProductController(product_repo)
    order_controller = OrderController(product_repo, customer_repo, invoice_repo)
    report_controller = ReportController(report_repo)
    return product_controller, order_controller, report_controller


def run() -> None:
    init_schema()
    seed_sample_products()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    font = QFont("Times New Roman")
    font.setPixelSize(MIN_FONT_PX)
    app.setFont(font)

    product_controller, order_controller, report_controller = build_controllers()

    window = MainWindow(product_controller, order_controller, report_controller)
    window.show()

    sys.exit(app.exec())
