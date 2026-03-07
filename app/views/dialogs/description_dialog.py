from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QTextEdit, QVBoxLayout


class DescriptionDialog(QDialog):
    def __init__(self, product_code: str, product_name: str, description: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mo ta san pham")
        self.setModal(True)
        self.resize(640, 420)

        title = QLabel(f"Ma san pham: {product_code} | Ten: {product_name}")

        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(description or "(Khong co mo ta)")

        close_btn = QPushButton("Dong")
        close_btn.clicked.connect(self.accept)

        root = QVBoxLayout(self)
        root.addWidget(title)
        root.addWidget(body)
        root.addWidget(close_btn)
