from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)

from app.utils.item_sort import sort_items_by_unit_price_desc
from app.views.dialogs import disable_minimize_button


def format_money(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


LIST_ROW_HEIGHT_PX = 35


class InvoiceDetailDialog(QDialog):
    def __init__(self, detail: dict, parent=None):
        super().__init__(parent)
        disable_minimize_button(self)
        self.setWindowTitle("Chi tiết hóa đơn")
        self.setModal(True)
        self.resize(980, 720)

        invoice = detail["invoice"]
        items = sort_items_by_unit_price_desc(detail["items"])

        header_box = QGroupBox("Thông tin hóa đơn")
        header_form = QFormLayout(header_box)
        header_form.addRow("Số hóa đơn", QLabel(invoice["invoice_no"]))
        header_form.addRow("Ngày tạo", QLabel(invoice["created_at"]))
        header_form.addRow("Tên khách hàng", QLabel(invoice["customer_name"]))
        header_form.addRow("Số điện thoại", QLabel(invoice.get("phone", "")))
        header_form.addRow("Gmail", QLabel(invoice.get("email", "")))
        header_form.addRow("Mã số thuế", QLabel(invoice.get("tax_code", "")))
        header_form.addRow("Địa chỉ", QLabel(invoice.get("address", "")))
        header_form.addRow("Tổng số tiền", QLabel(format_money(invoice["total_amount"])))

        items_box = QGroupBox("Danh sách sản phẩm")
        items_layout = QVBoxLayout(items_box)
        self.items_table = QTableWidget(len(items), 5)
        self.items_table.setHorizontalHeaderLabels(
            ["Mã sản phẩm", "Tên sản phẩm", "Số lượng", "Đơn giá", "Thành tiền"]
        )
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setWordWrap(True)
        self.items_table.setTextElideMode(Qt.ElideNone)
        self.items_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.items_table.verticalHeader().setMinimumSectionSize(LIST_ROW_HEIGHT_PX)
        self.items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        for row, item in enumerate(items):
            values = [
                item["product_code"],
                item["product_name"],
                str(item["quantity"]),
                format_money(item["unit_price"]),
                format_money(item["line_total"]),
            ]
            for col, value in enumerate(values):
                self.items_table.setItem(row, col, QTableWidgetItem(value))
        self.items_table.resizeRowsToContents()

        items_layout.addWidget(self.items_table)

        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(self.accept)

        root = QVBoxLayout(self)
        root.addWidget(header_box)
        root.addWidget(items_box)
        root.addWidget(close_btn)