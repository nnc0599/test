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


class ProductFormDialog(QDialog):
    def __init__(self, parent=None, mode: str = "add", initial: dict | None = None):
        super().__init__(parent)
        self.mode = mode
        self.initial = initial or {}

        self.setModal(True)
        self.resize(760, 560)
        self.setWindowTitle("Them san pham moi" if mode == "add" else "Sua thong tin san pham")

        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.warranty_edit = QLineEdit()
        self.unit_edit = QLineEdit()

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 1_000_000_000)

        self.price_spin = QSpinBox()
        self.price_spin.setRange(0, 2_000_000_000)

        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText("Nhap mo ta chi tiet")

        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("Vi du: Ngoc Chung - nhap 16 tam pin moi")
        self.note_label = QLabel("Ghi chu")
        self.note_label.setStyleSheet("color: #D62828; font-weight: 700;")

        top_grid = QGridLayout()
        top_grid.addWidget(QLabel("Ma san pham"), 0, 0)
        top_grid.addWidget(self.code_edit, 0, 1)
        top_grid.addWidget(QLabel("Ten san pham"), 0, 2)
        top_grid.addWidget(self.name_edit, 0, 3)

        top_grid.addWidget(QLabel("Bao hanh"), 1, 0)
        top_grid.addWidget(self.warranty_edit, 1, 1)
        top_grid.addWidget(QLabel("Don vi tinh"), 1, 2)
        top_grid.addWidget(self.unit_edit, 1, 3)

        top_grid.addWidget(QLabel("So luong"), 2, 0)
        top_grid.addWidget(self.quantity_spin, 2, 1)
        top_grid.addWidget(QLabel("Gia ban"), 2, 2)
        top_grid.addWidget(self.price_spin, 2, 3)

        product_box = QGroupBox("Thong tin san pham")
        product_box.setLayout(top_grid)

        description_box = QGroupBox("Mo ta chi tiet")
        description_layout = QVBoxLayout(description_box)
        description_layout.addWidget(self.description_edit)

        note_box = QGroupBox("Thong tin cap nhat")
        note_layout = QFormLayout(note_box)
        note_layout.addRow(self.note_label, self.note_edit)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal,
        )
        self.ok_button = self.buttons.button(QDialogButtonBox.Ok)
        self.cancel_button = self.buttons.button(QDialogButtonBox.Cancel)
        self.ok_button.setText("OK")
        self.cancel_button.setText("CANCEL")
        self.buttons.accepted.connect(self._validate_before_accept)
        self.buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(product_box)
        root.addWidget(description_box)
        if mode == "edit":
            root.addWidget(note_box)
        root.addWidget(self.buttons)

        self._bind_data()
        self._bind_rules()

    def _bind_data(self) -> None:
        self.code_edit.setText(self.initial.get("product_code", ""))
        self.name_edit.setText(self.initial.get("name", ""))
        self.warranty_edit.setText(self.initial.get("warranty", ""))
        self.unit_edit.setText(self.initial.get("unit", ""))
        self.quantity_spin.setValue(int(self.initial.get("quantity", 0)))
        self.price_spin.setValue(int(self.initial.get("sale_price", 0)))
        self.description_edit.setPlainText(self.initial.get("description", ""))
        self.note_edit.setPlainText(self.initial.get("note", ""))

        if self.mode == "edit":
            self.code_edit.setReadOnly(True)

    def _bind_rules(self) -> None:
        if self.mode == "edit":
            self.ok_button.setEnabled(bool(self.note_edit.toPlainText().strip()))
            self.note_edit.textChanged.connect(
                lambda: self.ok_button.setEnabled(bool(self.note_edit.toPlainText().strip()))
            )

    def _validate_before_accept(self) -> None:
        if not self.code_edit.text().strip():
            QMessageBox.warning(self, "Du lieu thieu", "Ban phai nhap ma san pham")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Du lieu thieu", "Ban phai nhap ten san pham")
            return
        if self.mode == "edit" and not self.note_edit.toPlainText().strip():
            QMessageBox.warning(
                self,
                "Thieu ghi chu",
                "Khong the cap nhat neu khong nhap ghi chu.",
            )
            return
        self.accept()

    def payload(self) -> dict:
        return {
            "product_code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "warranty": self.warranty_edit.text().strip(),
            "unit": self.unit_edit.text().strip(),
            "quantity": self.quantity_spin.value(),
            "sale_price": self.price_spin.value(),
            "description": self.description_edit.toPlainText().strip(),
            "note": self.note_edit.toPlainText().strip(),
        }
