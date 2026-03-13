from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)

from app.utils.invoice_docx import DOCUMENT_VARIANTS


def format_money(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


LIST_ROW_HEIGHT_PX = 35


class InvoicePreviewDialog(QDialog):
    def __init__(
        self,
        invoice: dict,
        items: list[dict],
        parent=None,
        document_kind: str = "invoice",
        show_confirm: bool = True,
        confirm_text: str | None = None,
        window_title: str | None = None,
        hint_text: str | None = None,
    ):
        super().__init__(parent)
        variant = DOCUMENT_VARIANTS.get(document_kind, DOCUMENT_VARIANTS["invoice"])
        self.setWindowTitle(window_title or str(variant["window_title"]))
        self.setModal(True)
        self.resize(980, 720)

        self._confirmed = False
        self._show_confirm = show_confirm

        root = QVBoxLayout(self)

        hint = QLabel(hint_text or str(variant["hint"]))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #475569; font-style: italic;")
        root.addWidget(hint)

        header_box = QGroupBox(self._build_header_title(document_kind))
        header_form = QFormLayout(header_box)
        for label, value in self._build_header_rows(invoice, document_kind):
            content = QLabel(value)
            content.setWordWrap(True)
            content.setTextInteractionFlags(Qt.TextSelectableByMouse)
            header_form.addRow(label, content)
        root.addWidget(header_box)

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
                str(item.get("product_code", "") or ""),
                str(item.get("product_name", "") or ""),
                str(item.get("quantity", 0) or 0),
                format_money(int(item.get("unit_price", 0) or 0)),
                format_money(int(item.get("line_total", 0) or 0)),
            ]
            for col, value in enumerate(values):
                self.items_table.setItem(row, col, QTableWidgetItem(value))
        self.items_table.resizeRowsToContents()

        items_layout.addWidget(self.items_table)
        root.addWidget(items_box, 1)

        actions = QHBoxLayout()
        actions.addStretch()

        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(self.reject)
        actions.addWidget(close_btn)

        self.confirm_btn = QPushButton(confirm_text or str(variant["confirm_text"]))
        self.confirm_btn.setStyleSheet(
            "QPushButton { background: #0EA5E9; color: white; font-weight: 800; }"
            "QPushButton:hover { background: #0284C7; }"
        )
        self.confirm_btn.clicked.connect(self._accept_export)
        if show_confirm:
            actions.addWidget(self.confirm_btn)
        else:
            self.confirm_btn.hide()

        root.addLayout(actions)

    def _accept_export(self) -> None:
        if not self._show_confirm:
            return
        self._confirmed = True
        self.accept()

    @staticmethod
    def _build_header_title(document_kind: str) -> str:
        if document_kind == "quotation":
            return "Thông tin bản báo giá"
        return "Thông tin hóa đơn"

    @staticmethod
    def _build_header_rows(invoice: dict, document_kind: str) -> list[tuple[str, str]]:
        reference_label = "Số báo giá" if document_kind == "quotation" else "Số hóa đơn"
        reference_value = str(invoice.get("quotation_no") or invoice.get("invoice_no") or "")
        rows = [
            (reference_label, reference_value),
            ("Ngày tạo", str(invoice.get("created_at", "") or "")),
            ("Tên khách hàng", str(invoice.get("customer_name", "") or "")),
            ("Số điện thoại", str(invoice.get("phone", "") or "")),
            ("Gmail", str(invoice.get("email", "") or "")),
            ("Mã số thuế", str(invoice.get("tax_code", "") or "")),
            ("Địa chỉ", str(invoice.get("address", "") or "")),
        ]

        if document_kind == "quotation":
            rows.append(("Tổng tiền hàng", format_money(int(invoice.get("goods_amount", 0) or 0))))
            rows.append(("Phí ship", format_money(int(invoice.get("ship_fee", 0) or 0))))
        rows.append(("Tổng số tiền", format_money(int(invoice.get("total_amount", 0) or 0))))
        return rows

    @property
    def confirmed(self) -> bool:
        return self._confirmed
