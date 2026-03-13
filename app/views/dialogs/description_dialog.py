from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QTextEdit, QVBoxLayout

from app.views.dialogs import disable_minimize_button


class DescriptionDialog(QDialog):
    def __init__(self, product_code: str, product_name: str, description: str, parent=None):
        super().__init__(parent)
        disable_minimize_button(self)
        self.setWindowTitle("Mô tả sản phẩm")
        self.setModal(True)
        self.resize(640, 420)

        title = QLabel(f"Mã sản phẩm: {product_code} | Tên: {product_name}")

        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(description or "(Không có mô tả)")

        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(self.accept)

        root = QVBoxLayout(self)
        root.addWidget(title)
        root.addWidget(body)
        root.addWidget(close_btn)
