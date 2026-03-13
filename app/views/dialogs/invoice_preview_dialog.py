from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from app.utils.invoice_docx import DOCUMENT_VARIANTS, build_invoice_preview_html
from app.views.dialogs import disable_minimize_button


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
        disable_minimize_button(self)
        variant = DOCUMENT_VARIANTS.get(document_kind, DOCUMENT_VARIANTS["invoice"])
        self.setWindowTitle(window_title or str(variant["window_title"]))
        self.setModal(True)
        self.resize(1100, 900)

        self._confirmed = False
        self._show_confirm = show_confirm

        root = QVBoxLayout(self)

        hint = QLabel(hint_text or str(variant["hint"]))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #475569; font-style: italic;")
        root.addWidget(hint)

        self.preview = QTextBrowser(self)
        self.preview.setOpenExternalLinks(False)
        self.preview.setOpenLinks(False)
        self.preview.setReadOnly(True)
        self.preview.setHtml(build_invoice_preview_html(invoice, items, document_kind=document_kind))
        self.preview.setStyleSheet(
            "QTextBrowser { background: #E5E7EB; border: none; padding: 18px; }"
        )
        root.addWidget(self.preview, 1)

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

    @property
    def confirmed(self) -> bool:
        return self._confirmed
