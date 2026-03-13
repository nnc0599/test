from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPageLayout, QPageSize, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.utils.invoice_docx import (
    DOCUMENT_VARIANTS,
    build_invoice_preview_pdf,
    has_pdf_preview_support,
)


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
        self._document_kind = document_kind
        self._document_title = self.windowTitle()
        self._document_name = self._build_document_name(invoice, document_kind)
        self._preview_dir = TemporaryDirectory(prefix="invoice-preview-")
        self._preview_pdf_path: Path | None = None
        self._pdf_document: QPdfDocument | None = None
        self.preview: QPdfView | None = None
        self._preview_unavailable_reason: str | None = None

        if has_pdf_preview_support():
            self._preview_pdf_path = self._build_preview_pdf(invoice, items)
            self._pdf_document = QPdfDocument(self)

            load_error = self._pdf_document.load(str(self._preview_pdf_path))
            if load_error != QPdfDocument.Error.None_:
                raise ValueError("Không thể mở bản xem trước PDF")
        else:
            self._preview_unavailable_reason = "Không tìm thấy LibreOffice để tạo bản xem trước PDF"

        root = QVBoxLayout(self)
        hint = QLabel(hint_text or str(variant["hint"]))
        hint.setStyleSheet("color: #475569; font-style: italic;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        if self._pdf_document is not None:
            self.preview = QPdfView(self)
            self.preview.setDocument(self._pdf_document)
            self.preview.setPageMode(QPdfView.PageMode.MultiPage)
            self.preview.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            self.preview.setStyleSheet("QPdfView { background: #E5E7EB; border: none; }")
            root.addWidget(self.preview, 1)
        else:
            unavailable_label = QLabel(
                "Không thể hiển thị bản xem trước PDF trên máy này. "
                "Bạn vẫn có thể tiếp tục để xuất file Word."
            )
            unavailable_label.setWordWrap(True)
            unavailable_label.setAlignment(Qt.AlignCenter)
            unavailable_label.setStyleSheet(
                "background: #FEF3C7; color: #92400E; border: 1px solid #F59E0B; "
                "border-radius: 12px; padding: 24px; font-weight: 600;"
            )
            root.addWidget(unavailable_label, 1)

            if self._preview_unavailable_reason:
                detail_label = QLabel(self._preview_unavailable_reason)
                detail_label.setWordWrap(True)
                detail_label.setAlignment(Qt.AlignCenter)
                detail_label.setStyleSheet("color: #78716C;")
                root.addWidget(detail_label)

        actions = QHBoxLayout()

        self.zoom_out_btn = QPushButton("Thu nhỏ")
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        self.zoom_out_btn.setEnabled(self.preview is not None)
        actions.addWidget(self.zoom_out_btn)

        self.fit_width_btn = QPushButton("Vừa chiều rộng")
        self.fit_width_btn.clicked.connect(self._fit_width)
        self.fit_width_btn.setEnabled(self.preview is not None)
        actions.addWidget(self.fit_width_btn)

        self.zoom_in_btn = QPushButton("Phóng to")
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        self.zoom_in_btn.setEnabled(self.preview is not None)
        actions.addWidget(self.zoom_in_btn)

        actions.addStretch()

        self.print_btn = QPushButton("In")
        self.print_btn.clicked.connect(self._print_preview)
        self.print_btn.setEnabled(self._pdf_document is not None)
        actions.addWidget(self.print_btn)

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

    def _print_preview(self) -> None:
        if self._pdf_document is None:
            QMessageBox.information(
                self,
                "Không có bản xem trước",
                self._preview_unavailable_reason or "Không có dữ liệu PDF để in.",
            )
            return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Portrait)
        printer.setDocName(self._document_name)

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle(f"In {self._document_title.lower()}")
        if dialog.exec() != QDialog.Accepted:
            return

        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(self, "Lỗi", "Không thể khởi tạo máy in")
            return

        try:
            page_rect = printer.pageLayout().paintRectPixels(printer.resolution())
            target_size = QSize(max(1, page_rect.width()), max(1, page_rect.height()))
            for page_index in range(self._pdf_document.pageCount()):
                if page_index > 0:
                    printer.newPage()
                image = self._pdf_document.render(page_index, target_size)
                if image.isNull():
                    continue
                x_pos = page_rect.x() + max(0, (page_rect.width() - image.width()) // 2)
                y_pos = page_rect.y() + max(0, (page_rect.height() - image.height()) // 2)
                painter.drawImage(x_pos, y_pos, image)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))
        finally:
            painter.end()

    def _zoom_in(self) -> None:
        if self.preview is None:
            return
        if self.preview.zoomMode() != QPdfView.ZoomMode.Custom:
            self.preview.setZoomMode(QPdfView.ZoomMode.Custom)
            self.preview.setZoomFactor(1.0)
        self.preview.setZoomFactor(self.preview.zoomFactor() * 1.15)

    def _zoom_out(self) -> None:
        if self.preview is None:
            return
        if self.preview.zoomMode() != QPdfView.ZoomMode.Custom:
            self.preview.setZoomMode(QPdfView.ZoomMode.Custom)
            self.preview.setZoomFactor(1.0)
        self.preview.setZoomFactor(max(0.2, self.preview.zoomFactor() / 1.15))

    def _fit_width(self) -> None:
        if self.preview is None:
            return
        self.preview.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def _build_preview_pdf(self, invoice: dict, items: list[dict]) -> Path:
        try:
            return build_invoice_preview_pdf(
                invoice,
                items,
                output_dir=Path(self._preview_dir.name),
                document_kind=self._document_kind,
                output_name=f"{self._document_name}.docx",
            )
        except Exception:
            self._preview_dir.cleanup()
            raise

    def closeEvent(self, event) -> None:
        self._preview_dir.cleanup()
        super().closeEvent(event)

    @staticmethod
    def _build_document_name(invoice: dict, document_kind: str) -> str:
        if document_kind == "quotation":
            reference = str(invoice.get("quotation_no") or invoice.get("invoice_no") or "bao-gia")
            return f"Bao-gia-{reference}"

        reference = str(invoice.get("invoice_no") or "hoa-don")
        return f"Hoa-don-{reference}"

    @property
    def confirmed(self) -> bool:
        return self._confirmed