from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from app.config import DEFAULT_ADMIN_PASSWORD


class PasswordDialog(QDialog):
    def __init__(self, parent=None, title: str = "Xác thực"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Nhập mật khẩu")
        self.password_edit.returnPressed.connect(self._accept_if_valid)

        self.info_label = QLabel("Hãy nhập mật khẩu để thực hiện thao tác. Mật khẩu mặc định: 12345678")
        self.info_label.setAlignment(Qt.AlignCenter)

        form = QFormLayout()
        form.addRow("Mật khẩu:", self.password_edit)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._accept_if_valid)
        self.buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(self.info_label)
        root.addLayout(form)
        root.addWidget(self.buttons)

        self.password_edit.setFocus()

    def _accept_if_valid(self) -> None:
        if self.password_edit.text() == DEFAULT_ADMIN_PASSWORD:
            self.accept()
            return
        self.info_label.setText("Sai mật khẩu, vui lòng thử lại")
        self.password_edit.selectAll()

    @staticmethod
    def verify(parent=None, title: str = "Xác thực") -> bool:
        dlg = PasswordDialog(parent=parent, title=title)
        return dlg.exec() == QDialog.Accepted
