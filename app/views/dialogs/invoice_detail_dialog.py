from __future__ import annotations

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


def format_money(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


class InvoiceDetailDialog(QDialog):
    def __init__(self, detail: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chi tiet hoa don")
        self.setModal(True)
        self.resize(980, 720)

        invoice = detail["invoice"]
        items = detail["items"]

        header_box = QGroupBox("Thong tin hoa don")
        header_form = QFormLayout(header_box)
        header_form.addRow("So hoa don", QLabel(invoice["invoice_no"]))
        header_form.addRow("Ngay tao", QLabel(invoice["created_at"]))
        header_form.addRow("Ten khach hang", QLabel(invoice["customer_name"]))
        header_form.addRow("So dien thoai", QLabel(invoice.get("phone", "")))
        header_form.addRow("Dia chi", QLabel(invoice.get("address", "")))
        header_form.addRow("Tong so tien", QLabel(format_money(invoice["total_amount"])))

        items_box = QGroupBox("Danh sach san pham")
        items_layout = QVBoxLayout(items_box)
        self.items_table = QTableWidget(len(items), 5)
        self.items_table.setHorizontalHeaderLabels(
            ["Ma san pham", "Ten san pham", "So luong", "Don gia", "Thanh tien"]
        )
        self.items_table.verticalHeader().setVisible(False)
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

        items_layout.addWidget(self.items_table)

        close_btn = QPushButton("Dong")
        close_btn.clicked.connect(self.accept)

        root = QVBoxLayout(self)
        root.addWidget(header_box)
        root.addWidget(items_box)
        root.addWidget(close_btn)