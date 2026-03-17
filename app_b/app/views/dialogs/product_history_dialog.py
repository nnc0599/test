from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.views.dialogs import disable_minimize_button


def format_money(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


LIST_ROW_HEIGHT_PX = 35


class ProductHistoryDialog(QDialog):
    def __init__(self, product: dict, history_rows: list[dict], parent=None):
        super().__init__(parent)
        disable_minimize_button(self)
        self.setModal(True)
        self.resize(1100, 720)
        self.setWindowTitle(f"Lịch sử chỉnh sửa - {product.get('product_code', '')}")

        product_box = QGroupBox("Thông tin sản phẩm hiện tại")
        product_form = QFormLayout(product_box)
        product_form.addRow("Mã sản phẩm", QLabel(product.get("product_code", "")))
        product_form.addRow("Tên sản phẩm", QLabel(product.get("name", "")))
        product_form.addRow("Đơn vị tính", QLabel(product.get("unit", "")))
        product_form.addRow("Số lượng", QLabel(str(product.get("quantity", 0))))
        product_form.addRow("Giá bán", QLabel(format_money(int(product.get("sale_price", 0)))))
        product_form.addRow("Mô tả", QLabel(product.get("description", "")))
        product_form.addRow("Ghi chú hiện tại", QLabel(product.get("note", "")))
        product_form.addRow("Ngày cập nhật", QLabel(product.get("updated_at", "")))

        history_box = QGroupBox("Lịch sử thay đổi số lượng và đơn giá")
        history_layout = QVBoxLayout(history_box)

        self.history_table = QTableWidget(len(history_rows), 8)
        self.history_table.setHorizontalHeaderLabels(
            [
                "Ngày sửa",
                "Mã sản phẩm",
                "Tên sản phẩm",
                "Đơn vị tính",
                "Số lượng",
                "Đơn giá",
                "Mô tả",
                "Ghi chú",
            ]
        )
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(LIST_ROW_HEIGHT_PX)
        self.history_table.verticalHeader().setMinimumSectionSize(LIST_ROW_HEIGHT_PX)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Stretch)

        for row, item in enumerate(history_rows):
            values = [
                item.get("changed_at", ""),
                item.get("product_code", ""),
                item.get("name", ""),
                item.get("unit", ""),
                str(item.get("quantity", 0)),
                format_money(int(item.get("sale_price", 0))),
                item.get("description", ""),
                item.get("note", ""),
            ]
            for col, value in enumerate(values):
                self.history_table.setItem(row, col, QTableWidgetItem(value))

        if not history_rows:
            self.history_table.setRowCount(1)
            self.history_table.setSpan(0, 0, 1, 8)
            self.history_table.setItem(
                0,
                0,
                QTableWidgetItem("Chưa có lịch sử thay đổi số lượng hoặc đơn giá cho sản phẩm này."),
            )

        history_layout.addWidget(self.history_table)

        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(self.accept)

        root = QVBoxLayout(self)
        root.addWidget(product_box)
        root.addWidget(history_box)
        root.addWidget(close_btn)