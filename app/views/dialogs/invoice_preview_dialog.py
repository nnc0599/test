from __future__ import annotations

from app.utils.invoice_docx import DOCUMENT_VARIANTS

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.utils.invoice_docx import PREVIEW_ASSET_DIR, build_invoice_preview_html


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
        self.resize(1100, 900)

        self._confirmed = False
        self._show_confirm = show_confirm

        root = QVBoxLayout(self)
        hint = QLabel(hint_text or str(variant["hint"]))
        hint.setStyleSheet("color: #475569; font-style: italic;")
        root.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #E5E7EB; }")

        page_host = QWidget()
        page_layout = QVBoxLayout(page_host)
        page_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        page_layout.setContentsMargins(24, 24, 24, 24)

        page_frame = QFrame()
        page_frame.setFixedWidth(840)
        page_frame.setStyleSheet(
            "QFrame { background: white; border: 1px solid #CBD5E1; border-radius: 8px; }"
        )

        frame_layout = QVBoxLayout(page_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        self.preview = QTextBrowser()
        self.preview.setReadOnly(True)
        self.preview.setOpenLinks(False)
        self.preview.setSearchPaths([str(PREVIEW_ASSET_DIR)])
        self.preview.setFrameShape(QFrame.NoFrame)
        self.preview.setStyleSheet(
            "QTextBrowser { background: white; color: #111827; padding: 0; border: none; }"
        )
        self.preview.setHtml(build_invoice_preview_html(invoice, items, document_kind=document_kind))

        frame_layout.addWidget(self.preview)
        page_layout.addWidget(page_frame)
        scroll.setWidget(page_host)
        root.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch()

        self.close_btn = QPushButton("Đóng")
        self.close_btn.clicked.connect(self.reject)
        actions.addWidget(self.close_btn)

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