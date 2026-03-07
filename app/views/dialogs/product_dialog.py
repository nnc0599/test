from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.utils.time_utils import now_iso_utc7


class ProductFormDialog(QDialog):
    def __init__(self, parent=None, mode: str = "add", initial: dict | None = None):
        super().__init__(parent)
        self.mode = mode
        self.initial = initial or {}
        self._payload_cache: dict | None = None

        self.setModal(True)
        self.resize(760, 560)
        self.setWindowTitle("Thêm sản phẩm mới" if mode == "add" else "Sửa thông tin sản phẩm")

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Ví dụ: SP003")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nhập tên sản phẩm")
        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("Ví dụ: cái, hộp, bộ")
        self.updated_at_value = QLabel("Tự động lấy thời gian hiện tại")

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 1_000_000_000)

        self.price_spin = QSpinBox()
        self.price_spin.setRange(0, 2_000_000_000)

        self.description_edit = QPlainTextEdit(self)
        self.description_edit.setPlaceholderText("Nhập mô tả chi tiết")

        self.note_edit = QPlainTextEdit(self)
        self.note_edit.setPlaceholderText("Ví dụ: Ngọc Chung - nhập 16 tấm pin mới")
        self.note_label = QLabel("Ghi chú", self)
        self.note_label.setStyleSheet("color: #D62828; font-weight: 700;")

        top_grid = QGridLayout()
        top_grid.addWidget(QLabel("Mã sản phẩm"), 0, 0)
        top_grid.addWidget(self.code_edit, 0, 1)
        top_grid.addWidget(QLabel("Tên sản phẩm"), 0, 2)
        top_grid.addWidget(self.name_edit, 0, 3)

        top_grid.addWidget(QLabel("Đơn vị tính"), 1, 0)
        top_grid.addWidget(self.unit_edit, 1, 1)
        top_grid.addWidget(QLabel("Số lượng"), 1, 2)
        top_grid.addWidget(self.quantity_spin, 1, 3)

        top_grid.addWidget(QLabel("Giá bán"), 2, 0)
        top_grid.addWidget(self.price_spin, 2, 1)
        top_grid.addWidget(QLabel("Ngày cập nhật"), 2, 2)
        top_grid.addWidget(self.updated_at_value, 2, 3)

        product_box = QGroupBox("Thông tin sản phẩm")
        product_box.setLayout(top_grid)

        description_box = QGroupBox("Mô tả chi tiết")
        description_layout = QVBoxLayout(description_box)
        description_layout.addWidget(self.description_edit)

        self.note_box = QGroupBox("Thông tin cập nhật", self)
        note_layout = QFormLayout(self.note_box)
        note_layout.addRow(self.note_label, self.note_edit)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal,
        )
        self.ok_button = self.buttons.button(QDialogButtonBox.Ok)
        self.cancel_button = self.buttons.button(QDialogButtonBox.Cancel)
        self.ok_button.setText("OK")
        self.cancel_button.setText("CANCEL")
        self.ok_button.setDefault(True)
        self.buttons.accepted.connect(self._validate_before_accept)
        self.buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(product_box)
        root.addWidget(description_box)
        if mode == "edit":
            root.addWidget(self.note_box)
        root.addWidget(self.buttons)

        self._bind_data()
        self._bind_rules()

    def _bind_data(self) -> None:
        self.code_edit.setText(self.initial.get("product_code", ""))
        self.name_edit.setText(self.initial.get("name", ""))
        self.unit_edit.setText(self.initial.get("unit", ""))
        self.quantity_spin.setValue(int(self.initial.get("quantity", 0)))
        self.price_spin.setValue(int(self.initial.get("sale_price", 0)))
        self.description_edit.setPlainText(self.initial.get("description", ""))
        self.note_edit.setPlainText(self.initial.get("note", ""))
        self.updated_at_value.setText(self.initial.get("updated_at", now_iso_utc7()))

        if self.mode == "edit":
            self.code_edit.setReadOnly(True)

        if self.mode == "add":
            self.code_edit.setFocus()

    def _bind_rules(self) -> None:
        if self.mode == "edit":
            self._sync_note_requirement()
            self.note_edit.textChanged.connect(self._sync_note_requirement)

    def _sync_note_requirement(self) -> None:
        self.ok_button.setEnabled(bool(self.note_edit.toPlainText().strip()))

    def _collect_payload(self) -> dict:
        return {
            "product_code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "unit": self.unit_edit.text().strip(),
            "quantity": self.quantity_spin.value(),
            "sale_price": self.price_spin.value(),
            "description": self.description_edit.toPlainText().strip(),
            "note": self.note_edit.toPlainText().strip(),
        }

    def _validate_before_accept(self) -> None:
        payload = self._collect_payload()

        if not payload["product_code"]:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Bạn phải nhập mã sản phẩm")
            return
        if not payload["name"]:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Bạn phải nhập tên sản phẩm")
            return
        if self.mode == "edit" and not payload["note"]:
            QMessageBox.warning(
                self,
                "Thiếu ghi chú",
                "Không thể cập nhật nếu không nhập ghi chú.",
            )
            return
        self._payload_cache = payload
        self.accept()

    def payload(self) -> dict:
        return dict(self._payload_cache or self._collect_payload())
