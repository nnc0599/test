from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


def format_money(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


class RecentQuotationsDialog(QDialog):
    def __init__(
        self,
        load_rows: Callable[[], list[dict]],
        on_edit: Callable[[int], bool],
        on_export: Callable[[int], bool],
        on_cancel: Callable[[int], bool],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Các bản báo giá gần đây")
        self.setModal(True)
        self.resize(980, 620)

        self._load_rows = load_rows
        self._on_edit = on_edit
        self._on_export = on_export
        self._on_cancel = on_cancel

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        heading = QLabel("Các bản báo giá gần đây")
        heading.setStyleSheet("font-size: 24px; font-weight: 900; color: #0F172A;")
        root.addWidget(heading)

        hint = QLabel("Chọn một bản báo giá trước, sau đó dùng các nút nổi bật bên dưới để sửa, xuất hóa đơn hoặc hủy đơn.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #475569; font-style: italic;")
        root.addWidget(hint)

        action_panel = QFrame()
        action_panel.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #EFF6FF, stop:1 #FEF2F2); border: 1px solid #DBEAFE; border-radius: 16px; }"
        )
        action_layout = QHBoxLayout(action_panel)
        action_layout.setContentsMargins(14, 14, 14, 14)
        action_layout.setSpacing(12)

        self.edit_btn = QPushButton("Sửa hóa đơn")
        self.export_btn = QPushButton("Xuất hóa đơn")
        self.cancel_btn = QPushButton("Hủy đơn")
        for button in [self.edit_btn, self.export_btn, self.cancel_btn]:
            button.setMinimumHeight(54)

        self.edit_btn.setStyleSheet(
            "QPushButton { background: #0EA5E9; color: white; font-weight: 900; border-radius: 14px; }"
            "QPushButton:hover { background: #0284C7; }"
            "QPushButton:disabled { background: #BAE6FD; color: #7C93A6; }"
        )
        self.export_btn.setStyleSheet(
            "QPushButton { background: #16A34A; color: white; font-weight: 900; border-radius: 14px; }"
            "QPushButton:hover { background: #15803D; }"
            "QPushButton:disabled { background: #BBF7D0; color: #6B7280; }"
        )
        self.cancel_btn.setStyleSheet(
            "QPushButton { background: #DC2626; color: white; font-weight: 900; border-radius: 14px; }"
            "QPushButton:hover { background: #B91C1C; }"
            "QPushButton:disabled { background: #FECACA; color: #6B7280; }"
        )

        action_layout.addWidget(self.edit_btn)
        action_layout.addWidget(self.export_btn)
        action_layout.addWidget(self.cancel_btn)
        root.addWidget(action_panel)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Họ tên", "Số điện thoại", "Tổng tiền hàng", "Ngày tạo đơn"])
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        root.addWidget(self.table, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(self.reject)
        footer.addWidget(close_btn)
        root.addLayout(footer)

        self.table.itemSelectionChanged.connect(self._sync_action_state)
        self.edit_btn.clicked.connect(self._handle_edit)
        self.export_btn.clicked.connect(self._handle_export)
        self.cancel_btn.clicked.connect(self._handle_cancel)

        self._action_effect = QGraphicsOpacityEffect(action_panel)
        action_panel.setGraphicsEffect(self._action_effect)
        self._action_anim = QPropertyAnimation(self._action_effect, b"opacity", self)
        self._action_anim.setDuration(360)
        self._action_anim.setStartValue(0.25)
        self._action_anim.setEndValue(1.0)
        self._action_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._action_anim.start()

        self.reload_rows()

    def _selected_quotation_id(self) -> int | None:
        current_row = self.table.currentRow()
        if current_row < 0:
            return None
        item = self.table.item(current_row, 0)
        if item is None:
            return None
        data = item.data(Qt.UserRole)
        return int(data) if data is not None else None

    def _sync_action_state(self) -> None:
        has_selection = self._selected_quotation_id() is not None
        self.edit_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)
        self.cancel_btn.setEnabled(has_selection)

    def reload_rows(self) -> None:
        rows = self._load_rows()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["customer_name"],
                row.get("phone", ""),
                format_money(int(row.get("goods_amount", 0))),
                row["created_at"],
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col_index == 0:
                    item.setData(Qt.UserRole, int(row["id"]))
                self.table.setItem(row_index, col_index, item)

        self.table.resizeRowsToContents()

        if rows:
            self.table.selectRow(0)
        self._sync_action_state()

    def _handle_edit(self) -> None:
        quotation_id = self._selected_quotation_id()
        if quotation_id is None:
            return
        if self._on_edit(quotation_id):
            self.accept()

    def _handle_export(self) -> None:
        quotation_id = self._selected_quotation_id()
        if quotation_id is None:
            return
        if self._on_export(quotation_id):
            self.reload_rows()

    def _handle_cancel(self) -> None:
        quotation_id = self._selected_quotation_id()
        if quotation_id is None:
            return
        if self._on_cancel(quotation_id):
            self.reload_rows()