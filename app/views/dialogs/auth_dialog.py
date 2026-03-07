from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.config import DEFAULT_ADMIN_PASSWORD


class PasswordDialog(QDialog):
    def __init__(self, parent=None, title: str = "Xac thuc"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Nhap mat khau")

        self.info_label = QLabel("Hay nhap mat khau de thuc hien thao tac")
        self.info_label.setAlignment(Qt.AlignCenter)

        form = QFormLayout()
        form.addRow("Mat khau:", self.password_edit)

        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("CANCEL")
        btn_ok.clicked.connect(self._accept_if_valid)
        btn_cancel.clicked.connect(self.reject)

        row = QHBoxLayout()
        row.addWidget(btn_ok)
        row.addWidget(btn_cancel)

        root = QVBoxLayout(self)
        root.addWidget(self.info_label)
        root.addLayout(form)
        root.addLayout(row)

    def _accept_if_valid(self) -> None:
        if self.password_edit.text() == DEFAULT_ADMIN_PASSWORD:
            self.accept()
            return
        self.info_label.setText("Sai mat khau, vui long thu lai")
        self.password_edit.selectAll()

    @staticmethod
    def verify(parent=None, title: str = "Xac thuc") -> bool:
        dlg = PasswordDialog(parent=parent, title=title)
        return dlg.exec() == QDialog.Accepted
