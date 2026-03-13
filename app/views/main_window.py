from __future__ import annotations

from typing import Any

from pathlib import Path

from PySide6.QtCore import QDate, QEvent, QEasingCurve, QPropertyAnimation, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import DEFAULT_HEIGHT, DEFAULT_WIDTH, MIN_FONT_PX
from app.controllers.order_controller import OrderController
from app.controllers.product_controller import ProductController
from app.controllers.report_controller import ReportController
from app.utils.invoice_docx import EXPORT_DIR
from app.utils.time_utils import now_iso_utc7
from app.utils.invoice_docx import build_invoice_output_name, build_quotation_output_name, export_invoice_docx, export_report_docx
from app.views.dialogs.auth_dialog import PasswordDialog
from app.views.dialogs.description_dialog import DescriptionDialog
from app.views.dialogs.invoice_detail_dialog import InvoiceDetailDialog
from app.views.dialogs.invoice_preview_dialog import InvoicePreviewDialog
from app.views.dialogs.product_history_dialog import ProductHistoryDialog
from app.views.dialogs.product_dialog import ProductFormDialog
from app.views.dialogs.recent_quotations_dialog import RecentQuotationsDialog


def format_money(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


LIST_ROW_HEIGHT_PX = 35
PRODUCT_LIST_ROW_HEIGHT_PX = 50


class MainWindow(QMainWindow):
    def __init__(
        self,
        product_controller: ProductController,
        order_controller: OrderController,
        report_controller: ReportController,
    ):
        super().__init__()
        self.product_controller = product_controller
        self.order_controller = order_controller
        self.report_controller = report_controller

        self.product_map: dict[str, dict[str, Any]] = {}
        self.invoice_lines: list[dict[str, Any]] = []
        self.selected_product_code: str | None = None
        self._editing_quotation_id: int | None = None
        self._editing_quotation_export_path = ""
        self._order_created_at_override: str | None = None
        self._suspend_product_search = False
        self._suspend_customer_search = False
        self._selected_product_stock = 0
        self._settings = QSettings("nnc0599", "PhanMemBanHang")
        self.invoice_export_dir = self._load_invoice_export_dir()

        self.setWindowTitle("Phần mềm bán hàng")
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.setMinimumSize(900, 600)

        self._apply_base_style()
        self._build_ui()
        self._apply_uniform_list_row_heights()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._bind_runtime_clock()
        self._sync_font_by_window_size()

        self.refresh_products()
        self.refresh_report()
        self._update_invoice_totals()

    def _apply_base_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #F6F7FB;
                color: #0F172A;
                selection-background-color: #E2E8F0;
                selection-color: #0F172A;
            }
            QGroupBox {
                border: 1px solid #D7DCE6;
                border-radius: 10px;
                margin-top: 10px;
                padding: 10px;
                font-weight: 600;
                background: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #334155;
            }
            QLineEdit, QSpinBox, QTableWidget, QPlainTextEdit {
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px;
                background: #FFFFFF;
            }
            QHeaderView::section {
                background: #E2E8F0;
                padding: 8px;
                border: none;
                border-right: 1px solid #CBD5E1;
                font-weight: 600;
            }
            QPushButton {
                border: none;
                border-radius: 10px;
                padding: 10px 14px;
                font-weight: 700;
                background: #CBD5E1;
                color: #0F172A;
            }
            QPushButton:hover {
                background: #94A3B8;
                color: white;
            }
            QPushButton:pressed {
                background: #64748B;
            }
            """
        )

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        self.menu_buttons: list[QPushButton] = []
        top_menu = QHBoxLayout()
        for idx, title in enumerate(["Lên đơn hàng", "Sản phẩm", "Báo cáo"]):
            btn = QPushButton(title)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(56)
            btn.clicked.connect(lambda checked=False, i=idx: self._switch_tab(i))
            top_menu.addWidget(btn)
            self.menu_buttons.append(btn)
        main_layout.addLayout(top_menu)

        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.stack)

        self.order_page = self._build_order_page()
        self.product_page = self._build_product_page()
        self.report_page = self._build_report_page()

        self.stack.addWidget(self.order_page)
        self.stack.addWidget(self.product_page)
        self.stack.addWidget(self.report_page)

        self._switch_tab(0)

    def _apply_uniform_list_row_heights(self) -> None:
        for widget in self.findChildren(QListWidget):
            widget.setSpacing(0)
            existing_style = widget.styleSheet().strip()
            item_style = (
                f"QListWidget::item {{ min-height: {LIST_ROW_HEIGHT_PX}px; "
                f"max-height: {LIST_ROW_HEIGHT_PX}px; }}"
            )
            if item_style not in existing_style:
                widget.setStyleSheet(f"{existing_style}\n{item_style}".strip())

        for widget in self.findChildren(QTableWidget):
            widget.setWordWrap(True)
            widget.setTextElideMode(Qt.ElideNone)
            widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            widget.verticalHeader().setMinimumSectionSize(LIST_ROW_HEIGHT_PX)

        if getattr(self, "product_table", None) is not None:
            self.product_table.verticalHeader().setDefaultSectionSize(PRODUCT_LIST_ROW_HEIGHT_PX)
            self.product_table.verticalHeader().setMinimumSectionSize(PRODUCT_LIST_ROW_HEIGHT_PX)

    def _build_order_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)

        customer_box = QGroupBox("Thông tin lên đơn")
        customer_grid = QGridLayout(customer_box)
        customer_grid.setHorizontalSpacing(8)
        customer_grid.setVerticalSpacing(6)

        self.order_name = QLineEdit()
        self.order_phone = QLineEdit()
        self.order_created_at = QLineEdit()
        self.order_created_at.setReadOnly(True)

        self.order_address = QLineEdit()
        self.order_email = QLineEdit()
        self.order_tax_code = QLineEdit()
        self.customer_suggestion_list = QListWidget()
        self.customer_suggestion_list.setAlternatingRowColors(True)
        self.customer_suggestion_list.setMaximumHeight(120)
        self.customer_suggestion_list.hide()

        customer_grid.addWidget(QLabel("Nhập họ tên"), 0, 0)
        customer_grid.addWidget(self.order_name, 0, 1)
        customer_grid.addWidget(QLabel("Số điện thoại"), 0, 2)
        customer_grid.addWidget(self.order_phone, 0, 3)
        customer_grid.addWidget(QLabel("Ngày tạo đơn"), 0, 4)
        customer_grid.addWidget(self.order_created_at, 0, 5)

        customer_grid.addWidget(QLabel("Địa chỉ"), 1, 0)
        customer_grid.addWidget(self.order_address, 1, 1)
        customer_grid.addWidget(QLabel("Gmail"), 1, 2)
        customer_grid.addWidget(self.order_email, 1, 3)
        customer_grid.addWidget(QLabel("Mã số thuế"), 1, 4)
        customer_grid.addWidget(self.order_tax_code, 1, 5)
        customer_grid.addWidget(self.customer_suggestion_list, 2, 1, 1, 5)

        customer_grid.setColumnStretch(1, 3)
        customer_grid.setColumnStretch(3, 2)
        customer_grid.setColumnStretch(5, 2)

        layout.addWidget(customer_box)

        add_item_box = QGroupBox("Thêm hàng hóa")
        add_grid = QGridLayout(add_item_box)
        add_grid.setHorizontalSpacing(8)
        add_grid.setVerticalSpacing(6)

        self.search_product_edit = QLineEdit()
        self.search_product_edit.setPlaceholderText("Tìm kiếm sản phẩm")
        self.search_product_list = QListWidget()
        self.search_product_list.setAlternatingRowColors(True)
        self.search_product_list.setMaximumHeight(140)
        self.search_product_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_product_list.hide()

        self.order_qty_spin = QSpinBox()
        self.order_qty_spin.setRange(1, 1_000_000_000)
        self.order_price_spin = QSpinBox()
        self.order_price_spin.setRange(0, 2_000_000_000)

        self.add_line_btn = QPushButton("Thêm vào danh sách")
        self.add_line_btn.clicked.connect(self._append_invoice_line)

        add_grid.addWidget(QLabel("Tìm kiếm sản phẩm"), 0, 0)
        add_grid.addWidget(self.search_product_edit, 0, 1, 1, 3)
        add_grid.addWidget(QLabel("Số lượng"), 0, 4)
        add_grid.addWidget(self.order_qty_spin, 0, 5)
        add_grid.addWidget(QLabel("Đơn giá"), 0, 6)
        add_grid.addWidget(self.order_price_spin, 0, 7)
        add_grid.addWidget(self.add_line_btn, 0, 8)
        add_grid.addWidget(self.search_product_list, 1, 0, 1, 9)

        layout.addWidget(add_item_box)

        self.order_table = QTableWidget(0, 7)
        self.order_table.setHorizontalHeaderLabels(
            ["STT", "Mã hàng", "Tên sản phẩm", "Số lượng", "Đơn giá", "Thành tiền", "Xóa"]
        )
        self.order_table.verticalHeader().setVisible(False)
        self.order_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.order_table.setSelectionBehavior(QTableWidget.SelectRows)
        header = self.order_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        layout.addWidget(self.order_table)

        self.payment_box = QGroupBox("Tổng tiền hóa đơn")
        self.payment_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        payment_layout = QVBoxLayout(self.payment_box)
        payment_layout.setContentsMargins(6, 4, 6, 4)
        payment_layout.setSpacing(2)

        self.total_all_text_label = QLabel("Tổng số tiền")
        self.total_all_label = QLabel("0")
        self.total_all_text_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.total_all_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        total_row = QHBoxLayout()
        total_row.setContentsMargins(0, 0, 0, 0)
        total_row.setSpacing(4)
        total_row.addWidget(self.total_all_text_label)
        total_row.addWidget(self.total_all_label)
        total_row.addStretch(1)

        payment_layout.addLayout(total_row)

        self._apply_payment_summary_fonts()

        layout.addWidget(self.payment_box)

        self.export_location_box = QGroupBox("Nơi lưu file hóa đơn / báo giá")
        self.export_location_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        export_location_layout = QHBoxLayout(self.export_location_box)
        export_location_layout.setContentsMargins(6, 4, 6, 4)
        export_location_layout.setSpacing(6)
        self.export_dir_label = QLabel(str(self.invoice_export_dir))
        self.export_dir_label.setWordWrap(True)
        self.export_dir_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.choose_export_dir_btn = QPushButton("Chọn nơi lưu file")
        self.choose_export_dir_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.choose_export_dir_btn.clicked.connect(self._choose_invoice_export_dir)
        export_location_layout.addWidget(self.export_dir_label, 1)
        export_location_layout.addWidget(self.choose_export_dir_btn)
        layout.addWidget(self.export_location_box)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.save_quote_btn = QPushButton("Lưu bản báo giá")
        self.view_quote_btn = QPushButton("Xem bản báo giá")
        self.export_btn = QPushButton("Xuất hóa đơn")

        self.save_quote_btn.setMinimumHeight(50)
        self.view_quote_btn.setMinimumHeight(50)
        self.export_btn.setMinimumHeight(50)

        self.save_quote_btn.setStyleSheet(
            "QPushButton { background: #F59E0B; color: white; font-weight: 900; }"
            "QPushButton:hover { background: #D97706; }"
            "QPushButton:pressed { background: #B45309; }"
        )
        self.view_quote_btn.setStyleSheet(
            "QPushButton { background: #7C3AED; color: white; font-weight: 900; }"
            "QPushButton:hover { background: #6D28D9; }"
            "QPushButton:pressed { background: #5B21B6; }"
        )
        self.export_btn.setStyleSheet(
            "QPushButton { background: #0EA5E9; color: white; font-weight: 900; }"
            "QPushButton:hover { background: #0284C7; }"
            "QPushButton:pressed { background: #0369A1; }"
        )

        self.save_quote_btn.clicked.connect(self._save_quotation)
        self.view_quote_btn.clicked.connect(self._open_recent_quotations)
        self.export_btn.clicked.connect(self._export_invoice)

        action_row.addWidget(self.save_quote_btn)
        action_row.addWidget(self.view_quote_btn)
        action_row.addWidget(self.export_btn)
        layout.addLayout(action_row)

        self.search_product_edit.textChanged.connect(self._refresh_product_suggestions)
        self.search_product_edit.returnPressed.connect(self._pick_product_from_input)
        self.search_product_list.itemClicked.connect(self._on_product_suggestion_clicked)
        self.order_name.textChanged.connect(self._refresh_customer_suggestions_from_inputs)
        self.order_phone.textChanged.connect(self._refresh_customer_suggestions_from_inputs)
        self.order_email.textChanged.connect(self._refresh_customer_suggestions_from_inputs)
        self.order_tax_code.textChanged.connect(self._refresh_customer_suggestions_from_inputs)
        self.customer_suggestion_list.itemClicked.connect(self._on_customer_suggestion_clicked)

        self._sync_order_table_widths()

        return page

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if event.type() == QEvent.MouseButtonPress:
            global_position = event.globalPosition().toPoint()
            clicked_widget = QApplication.widgetAt(global_position)
            self._hide_suggestion_lists_if_needed(clicked_widget)
        return super().eventFilter(watched, event)

    def _widget_is_within(self, widget: QWidget | None, container: QWidget) -> bool:
        current = widget
        while current is not None:
            if current is container:
                return True
            current = current.parentWidget()
        return False

    def _hide_suggestion_lists_if_needed(self, clicked_widget: QWidget | None) -> None:
        if self.search_product_list.isVisible() and not any(
            self._widget_is_within(clicked_widget, widget)
            for widget in [self.search_product_list, self.search_product_edit]
        ):
            self.search_product_list.hide()

        if self.customer_suggestion_list.isVisible() and not any(
            self._widget_is_within(clicked_widget, widget)
            for widget in [
                self.customer_suggestion_list,
                self.order_name,
                self.order_phone,
                self.order_address,
                self.order_email,
                self.order_tax_code,
            ]
        ):
            self.customer_suggestion_list.hide()

        if getattr(self, "invoice_suggestion_list", None) is not None and self.invoice_suggestion_list.isVisible() and not any(
            self._widget_is_within(clicked_widget, widget)
            for widget in [self.invoice_suggestion_list, self.invoice_search_edit]
        ):
            self.invoice_suggestion_list.hide()

    def _build_product_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        actions = QHBoxLayout()
        self.btn_add_product = QPushButton("Thêm sản phẩm")
        self.btn_edit_product = QPushButton("Sửa thông tin")
        self.btn_product_history = QPushButton("Lịch sử sửa đổi")
        self.btn_delete_product = QPushButton("Xóa sản phẩm")

        self.btn_add_product.setStyleSheet(
            "QPushButton { background: #22C55E; color: #0B1A10; }"
            "QPushButton:hover { background: #16A34A; color: white; }"
        )
        self.btn_edit_product.setStyleSheet(
            "QPushButton { background: #FDBA74; color: #4A2A00; }"
            "QPushButton:hover { background: #FB923C; color: white; }"
            "QPushButton:disabled { background: #FED7AA; color: #9A3412; }"
        )
        self.btn_product_history.setStyleSheet(
            "QPushButton { background: #93C5FD; color: #102A43; }"
            "QPushButton:hover { background: #60A5FA; color: white; }"
            "QPushButton:disabled { background: #BFDBFE; color: #1E3A8A; }"
        )
        self.btn_delete_product.setStyleSheet(
            "QPushButton { background: #FCA5A5; color: #4C1D1D; }"
            "QPushButton:hover { background: #F87171; color: white; }"
            "QPushButton:disabled { background: #FECACA; color: #7F1D1D; }"
        )

        for btn in [self.btn_add_product, self.btn_edit_product, self.btn_product_history, self.btn_delete_product]:
            btn.setMinimumHeight(56)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            actions.addWidget(btn)

        layout.addLayout(actions)

        self.product_table = QTableWidget(0, 6)
        self.product_table.setHorizontalHeaderLabels(
            ["Mã sản phẩm", "Tên sản phẩm", "Số lượng", "Giá bán", "Mô tả", "Ngày cập nhật"]
        )
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.product_table.setSelectionBehavior(QTableWidget.SelectRows)

        p_header = self.product_table.horizontalHeader()
        p_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        p_header.setSectionResizeMode(1, QHeaderView.Stretch)
        p_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        p_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        p_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        p_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        layout.addWidget(self.product_table)

        self.btn_edit_product.setEnabled(False)
        self.btn_product_history.setEnabled(False)
        self.btn_delete_product.setEnabled(False)

        self.btn_add_product.clicked.connect(self._on_add_product)
        self.btn_edit_product.clicked.connect(self._on_edit_product)
        self.btn_product_history.clicked.connect(self._on_view_product_history)
        self.btn_delete_product.clicked.connect(self._on_delete_product)
        self.product_table.itemSelectionChanged.connect(self._sync_product_action_state)

        return page

    def _build_report_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        hero = QFrame()
        hero.setStyleSheet(
            "QFrame {"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #E0F2FE, stop:1 #F8FAFC);"
            "border: 1px solid #BFDBFE; border-radius: 16px; }"
            "QLabel { background: transparent; color: #0F172A; }"
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 10, 18, 10)
        hero_layout.setSpacing(16)

        title_label = QLabel("Trung tâm báo cáo")
        title_label.setStyleSheet("font-size: 16px; font-weight: 800; color: #0F172A;")

        hero_refresh_btn = QPushButton("Làm mới dữ liệu")
        hero_refresh_btn.setMinimumHeight(34)
        hero_refresh_btn.setStyleSheet(
            "QPushButton { background: #0F172A; color: white; font-weight: 700; }"
            "QPushButton:hover { background: #1E293B; }"
        )
        hero_refresh_btn.clicked.connect(self.refresh_report)

        hero_layout.addWidget(title_label)
        hero_layout.addStretch(1)
        hero_layout.addWidget(hero_refresh_btn)
        layout.addWidget(hero)

        report_panels = QHBoxLayout()
        report_panels.setSpacing(12)

        revenue_group = QGroupBox("Báo cáo doanh thu")
        revenue_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        revenue_group.setFixedHeight(202)
        revenue_layout = QVBoxLayout(revenue_group)
        revenue_layout.setContentsMargins(10, 8, 10, 8)
        revenue_layout.setSpacing(6)

        revenue_controls = QGridLayout()
        revenue_controls.setSpacing(8)
        revenue_controls.addWidget(QLabel("Xem theo"), 0, 0)

        self.revenue_period_type_combo = QComboBox()
        self.revenue_period_type_combo.addItem("Ngày", "day")
        self.revenue_period_type_combo.addItem("Tháng", "month")
        self.revenue_period_type_combo.addItem("Năm", "year")
        self.revenue_period_type_combo.setMinimumWidth(120)
        revenue_controls.addWidget(self.revenue_period_type_combo, 0, 1)

        revenue_controls.addWidget(QLabel("Kỳ báo cáo"), 0, 2)
        self.revenue_period_edit = QDateEdit(QDate.currentDate())
        self.revenue_period_edit.setMinimumWidth(150)
        revenue_controls.addWidget(self.revenue_period_edit, 0, 3)

        self.export_revenue_report_btn = QPushButton("Xuất báo cáo doanh thu")
        self.export_revenue_report_btn.setMinimumHeight(38)
        self.export_revenue_report_btn.setStyleSheet(
            "QPushButton { background: #0284C7; color: white; }"
            "QPushButton:hover { background: #0369A1; }"
        )
        revenue_controls.addWidget(self.export_revenue_report_btn, 1, 0, 1, 4)
        revenue_controls.setColumnStretch(1, 1)
        revenue_controls.setColumnStretch(3, 1)
        revenue_layout.addLayout(revenue_controls)

        revenue_cards = QHBoxLayout()
        revenue_cards.setSpacing(6)
        self.revenue_total_card = self._build_report_metric_card("Tổng doanh thu", "#0EA5E9")
        self.revenue_count_card = self._build_report_metric_card("Số hóa đơn", "#14B8A6")
        revenue_cards.addWidget(self.revenue_total_card)
        revenue_cards.addWidget(self.revenue_count_card)
        revenue_layout.addLayout(revenue_cards)
        report_panels.addWidget(revenue_group, 1)

        goods_group = QGroupBox("Báo cáo hàng hóa")
        goods_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        goods_group.setFixedHeight(202)
        goods_layout = QVBoxLayout(goods_group)
        goods_layout.setContentsMargins(10, 8, 10, 8)
        goods_layout.setSpacing(6)

        goods_controls = QGridLayout()
        goods_controls.setSpacing(8)
        goods_controls.addWidget(QLabel("Loại báo cáo"), 0, 0)

        self.goods_report_type_combo = QComboBox()
        self.goods_report_type_combo.addItem("Sản phẩm đã bán", "sold")
        self.goods_report_type_combo.addItem("Sản phẩm tồn kho", "stock")
        self.goods_report_type_combo.setMinimumWidth(150)
        goods_controls.addWidget(self.goods_report_type_combo, 0, 1)

        goods_controls.addWidget(QLabel("Xem theo"), 0, 2)
        self.goods_period_type_combo = QComboBox()
        self.goods_period_type_combo.addItem("Ngày", "day")
        self.goods_period_type_combo.addItem("Tháng", "month")
        self.goods_period_type_combo.addItem("Năm", "year")
        self.goods_period_type_combo.setCurrentIndex(1)
        self.goods_period_type_combo.setMinimumWidth(120)
        goods_controls.addWidget(self.goods_period_type_combo, 0, 3)

        goods_controls.addWidget(QLabel("Kỳ báo cáo"), 1, 0)
        self.goods_period_edit = QDateEdit(QDate.currentDate())
        self.goods_period_edit.setMinimumWidth(150)
        goods_controls.addWidget(self.goods_period_edit, 1, 1)

        self.export_goods_report_btn = QPushButton("Xuất báo cáo hàng hóa")
        self.export_goods_report_btn.setMinimumHeight(38)
        self.export_goods_report_btn.setStyleSheet(
            "QPushButton { background: #15803D; color: white; }"
            "QPushButton:hover { background: #166534; }"
        )
        goods_controls.addWidget(self.export_goods_report_btn, 1, 2, 1, 2)
        goods_controls.setColumnStretch(1, 1)
        goods_controls.setColumnStretch(3, 1)
        goods_layout.addLayout(goods_controls)

        goods_cards = QHBoxLayout()
        goods_cards.setSpacing(6)
        self.goods_primary_card = self._build_report_metric_card("Tổng số lượng", "#F59E0B")
        self.goods_secondary_card = self._build_report_metric_card("Giá trị / doanh thu", "#22C55E")
        goods_cards.addWidget(self.goods_primary_card)
        goods_cards.addWidget(self.goods_secondary_card)
        goods_layout.addLayout(goods_cards)
        report_panels.addWidget(goods_group, 1)

        layout.addLayout(report_panels)

        invoice_group = QGroupBox("Hóa đơn")
        invoice_layout = QVBoxLayout(invoice_group)
        invoice_layout.setSpacing(8)

        invoice_search_layout = QGridLayout()
        invoice_search_layout.setSpacing(8)
        invoice_search_layout.addWidget(QLabel("Tìm kiếm"), 0, 0)

        self.invoice_search_edit = QLineEdit()
        self.invoice_search_edit.setPlaceholderText("Nhập mã hóa đơn, họ tên hoặc số điện thoại")
        invoice_search_layout.addWidget(self.invoice_search_edit, 0, 1)

        invoice_search_layout.addWidget(QLabel("Lọc theo"), 0, 2)

        self.invoice_filter_type_combo = QComboBox()
        self.invoice_filter_type_combo.addItem("Tất cả", "all")
        self.invoice_filter_type_combo.addItem("Ngày", "day")
        self.invoice_filter_type_combo.addItem("Tháng", "month")
        self.invoice_filter_type_combo.setMinimumWidth(110)
        invoice_search_layout.addWidget(self.invoice_filter_type_combo, 0, 3)

        self.invoice_filter_date_edit = QDateEdit(QDate.currentDate())
        self.invoice_filter_date_edit.setMinimumWidth(130)
        invoice_search_layout.addWidget(self.invoice_filter_date_edit, 0, 4)

        invoice_search_layout.setColumnStretch(1, 1)
        layout.addWidget(invoice_group)
        invoice_layout.addLayout(invoice_search_layout)

        self.invoice_suggestion_list = QListWidget()
        self.invoice_suggestion_list.setAlternatingRowColors(True)
        self.invoice_suggestion_list.setMaximumHeight(112)
        self.invoice_suggestion_list.hide()
        invoice_layout.addWidget(self.invoice_suggestion_list)

        self.invoice_table = QTableWidget(0, 6)
        self.invoice_table.setHorizontalHeaderLabels(
            ["Số hóa đơn", "Ngày tạo", "Khách hàng", "Số điện thoại", "Tổng tiền", "Xem hóa đơn"]
        )
        self.invoice_table.verticalHeader().setVisible(False)
        self.invoice_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.invoice_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.invoice_table.setAlternatingRowColors(True)
        invoice_header = self.invoice_table.horizontalHeader()
        invoice_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(2, QHeaderView.Stretch)
        invoice_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.invoice_table.setMinimumHeight(202)
        invoice_layout.addWidget(self.invoice_table)

        self.revenue_period_type_combo.currentIndexChanged.connect(self._on_revenue_period_changed)
        self.revenue_period_edit.dateChanged.connect(lambda _date: self.refresh_report())
        self.export_revenue_report_btn.clicked.connect(self._export_revenue_report)

        self.goods_report_type_combo.currentIndexChanged.connect(self._on_goods_report_mode_changed)
        self.goods_period_type_combo.currentIndexChanged.connect(self._on_goods_period_changed)
        self.goods_period_edit.dateChanged.connect(lambda _date: self.refresh_report())
        self.export_goods_report_btn.clicked.connect(self._export_goods_report)

        self.invoice_search_edit.textChanged.connect(lambda _text: self._refresh_invoice_search_results())
        self.invoice_filter_type_combo.currentIndexChanged.connect(self._on_invoice_filter_changed)
        self.invoice_filter_date_edit.dateChanged.connect(lambda _date: self._refresh_invoice_search_results())
        self.invoice_suggestion_list.itemClicked.connect(self._on_invoice_suggestion_clicked)

        self._on_revenue_period_changed()
        self._on_goods_period_changed()
        self._sync_goods_report_mode()
        self._on_invoice_filter_changed()

        return page

    def _build_report_metric_card(self, title: str, accent_color: str) -> QFrame:
        card = QFrame()
        card.setFixedHeight(66)
        card.setStyleSheet(
            f"QFrame {{ background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 6px solid {accent_color}; border-radius: 14px; }}"
            "QLabel { background: transparent; color: #0F172A; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 4, 10, 2)
        card_layout.setSpacing(0)
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
        value_label = QLabel("0")
        value_label.setStyleSheet("font-size: 17px; font-weight: 800; color: #0F172A;")
        note_label = QLabel("")
        note_label.setWordWrap(True)
        note_label.setStyleSheet("font-size: 13px; color: #64748B;")
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card_layout.addWidget(note_label)
        card.value_label = value_label  # type: ignore[attr-defined]
        card.note_label = note_label  # type: ignore[attr-defined]
        return card

    def _bind_runtime_clock(self) -> None:
        self._refresh_clock()
        timer = QTimer(self)
        timer.setInterval(1000)
        timer.timeout.connect(self._refresh_clock)
        timer.start()
        self._clock_timer = timer

    def _refresh_clock(self) -> None:
        self.order_created_at.setText(self._order_created_at_override or now_iso_utc7())

    def _apply_period_editor_format(self, editor: QDateEdit, period_type: str) -> None:
        if period_type == "day":
            editor.setDisplayFormat("dd/MM/yyyy")
            editor.setCalendarPopup(True)
        elif period_type == "month":
            editor.setDisplayFormat("MM/yyyy")
            editor.setCalendarPopup(True)
        elif period_type == "all":
            editor.setDisplayFormat("dd/MM/yyyy")
            editor.setCalendarPopup(True)
        else:
            editor.setDisplayFormat("yyyy")
            editor.setCalendarPopup(False)

    def _selected_period(self, combo: QComboBox, editor: QDateEdit) -> tuple[str, str]:
        period_type = str(combo.currentData() or "day")
        date_value = editor.date()
        if period_type == "day":
            return period_type, date_value.toString("yyyy-MM-dd")
        if period_type == "month":
            return period_type, date_value.toString("yyyy-MM")
        return period_type, date_value.toString("yyyy")

    def _period_label(self, period_type: str, period_value: str) -> str:
        if period_type == "day":
            year, month, day = period_value.split("-")
            return f"Ngày {day}/{month}/{year}"
        if period_type == "month":
            year, month = period_value.split("-")
            return f"Tháng {month}/{year}"
        return f"Năm {period_value}"

    def _set_metric_card_value(self, card: QFrame, value_text: str, note_text: str) -> None:
        card.value_label.setText(value_text)  # type: ignore[attr-defined]
        card.note_label.setText(note_text)  # type: ignore[attr-defined]
        card.note_label.setVisible(bool(note_text))  # type: ignore[attr-defined]

    def _on_revenue_period_changed(self) -> None:
        period_type = str(self.revenue_period_type_combo.currentData() or "day")
        self._apply_period_editor_format(self.revenue_period_edit, period_type)
        self.refresh_report()

    def _on_goods_period_changed(self) -> None:
        period_type = str(self.goods_period_type_combo.currentData() or "day")
        self._apply_period_editor_format(self.goods_period_edit, period_type)
        self.refresh_report()

    def _sync_goods_report_mode(self) -> None:
        report_type = str(self.goods_report_type_combo.currentData() or "sold")
        use_period = report_type == "sold"
        self.goods_period_type_combo.setEnabled(use_period)
        self.goods_period_edit.setEnabled(use_period)

    def _selected_invoice_filter(self) -> tuple[str, str]:
        period_type = str(self.invoice_filter_type_combo.currentData() or "all")
        if period_type == "all":
            return period_type, ""
        if period_type == "day":
            return period_type, self.invoice_filter_date_edit.date().toString("yyyy-MM-dd")
        return period_type, self.invoice_filter_date_edit.date().toString("yyyy-MM")

    def _on_invoice_filter_changed(self) -> None:
        period_type = str(self.invoice_filter_type_combo.currentData() or "all")
        self._apply_period_editor_format(self.invoice_filter_date_edit, period_type)
        self.invoice_filter_date_edit.setEnabled(period_type != "all")
        self._refresh_invoice_search_results()

    def _refresh_invoice_search_results(self, keyword: str | None = None) -> None:
        normalized_keyword = (keyword if keyword is not None else self.invoice_search_edit.text()).strip()
        filter_type, filter_value = self._selected_invoice_filter()
        invoices = self.order_controller.search_invoices(normalized_keyword, filter_type, filter_value)
        self._render_invoice_rows(invoices)

        self.invoice_suggestion_list.clear()
        if not normalized_keyword:
            self.invoice_suggestion_list.hide()
            return

        for invoice in invoices[:10]:
            label = (
                f"{invoice['invoice_no']} | {invoice['customer_name']} | {invoice.get('phone', '')} | {invoice['created_at']}"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, invoice["invoice_no"])
            self.invoice_suggestion_list.addItem(item)

        self.invoice_suggestion_list.setVisible(self.invoice_suggestion_list.count() > 0)
        if self.invoice_suggestion_list.count() > 0:
            self.invoice_suggestion_list.setCurrentRow(0)

    def _on_invoice_suggestion_clicked(self, item: QListWidgetItem) -> None:
        invoice_no = item.data(Qt.UserRole)
        if not invoice_no:
            return
        self.invoice_search_edit.setText(str(invoice_no))
        self.invoice_suggestion_list.hide()

    def _render_invoice_rows(self, invoices: list[dict]) -> None:
        self.invoice_table.setRowCount(len(invoices))
        for row, invoice in enumerate(invoices):
            values = [
                invoice["invoice_no"],
                invoice["created_at"],
                invoice["customer_name"],
                invoice.get("phone", ""),
                format_money(invoice["total_amount"]),
            ]
            for col, value in enumerate(values):
                self.invoice_table.setItem(row, col, QTableWidgetItem(value))

            view_btn = QPushButton("Xem hóa đơn")
            view_btn.setStyleSheet(
                "QPushButton { background: #E0F2FE; color: #075985; font-weight: 700; }"
                "QPushButton:hover { background: #BAE6FD; }"
            )
            view_btn.clicked.connect(
                lambda checked=False, invoice_no=invoice["invoice_no"]: self._open_invoice_preview(invoice_no)
            )
            self.invoice_table.setCellWidget(row, 5, view_btn)
        self.invoice_table.resizeRowsToContents()

    def _open_invoice_preview(self, invoice_no: str) -> None:
        detail = self.order_controller.get_invoice_detail(invoice_no)
        if not detail:
            QMessageBox.warning(self, "Không tìm thấy", "Không lấy được chi tiết hóa đơn")
            return

        try:
            preview_dialog = InvoicePreviewDialog(detail["invoice"], detail["items"], self)
            preview_dialog.exec()
            if not preview_dialog.confirmed:
                return

            export_path = export_invoice_docx(
                detail["invoice"],
                detail["items"],
                self.invoice_export_dir,
                output_name=build_invoice_output_name(invoice_no, detail["invoice"].get("customer_name", "")),
            )
            self._warn_open_export_failure(export_path)
        except Exception as exc:  # pragma: no cover - dialog feedback
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_goods_report_mode_changed(self) -> None:
        self._sync_goods_report_mode()
        self.refresh_report()

    def _export_revenue_report(self) -> None:
        period_type = getattr(self, "_current_revenue_period_type", "day")
        period_value = getattr(self, "_current_revenue_period_value", QDate.currentDate().toString("yyyy-MM-dd"))
        summary = getattr(self, "_current_revenue_summary", {"invoice_count": 0, "total_amount": 0})
        rows = getattr(self, "_current_revenue_rows", [])
        period_label = self._period_label(period_type, period_value)

        data_rows = [
            [
                item["invoice_no"],
                item["created_at"],
                item["customer_name"],
                item.get("phone", ""),
                format_money(item["total_amount"]),
            ]
            for item in rows
        ]

        file_name = f"bao_cao_doanh_thu_{period_type}_{period_value}.docx"
        report_path = export_report_docx(
            report_title="BÁO CÁO DOANH THU",
            period_label=period_label,
            summary_rows=[
                ("Số hóa đơn", str(summary["invoice_count"])),
                ("Tổng doanh thu", format_money(summary["total_amount"])),
            ],
            headers=["Số hóa đơn", "Ngày tạo", "Khách hàng", "SĐT", "Tổng tiền"],
            data_rows=data_rows,
            output_name=file_name,
            column_widths_cm=[2.5, 4.0, 6.0, 2.8, 2.8],
            centered_columns={0, 1, 3, 4},
            output_dir=self.invoice_export_dir,
        )
        self._warn_open_export_failure(report_path)

    def _export_goods_report(self) -> None:
        report_type = getattr(self, "_current_goods_report_type", "sold")
        rows = getattr(self, "_current_goods_rows", [])

        if report_type == "sold":
            period_type = getattr(self, "_current_goods_period_type", "day")
            period_value = getattr(self, "_current_goods_period_value", QDate.currentDate().toString("yyyy-MM-dd"))
            summary = getattr(self, "_current_goods_summary", {"product_count": 0, "total_quantity": 0, "total_amount": 0})
            period_label = self._period_label(period_type, period_value)
            data_rows = [
                [
                    item["product_code"],
                    item["product_name"],
                    item.get("unit", ""),
                    str(item["sold_quantity"]),
                    format_money(item["sold_amount"]),
                ]
                for item in rows
            ]
            file_name = f"bao_cao_hang_hoa_da_ban_{period_type}_{period_value}.docx"
            report_title = "BÁO CÁO HÀNG HÓA - SẢN PHẨM ĐÃ BÁN"
            summary_rows = [
                ("Số sản phẩm", str(summary["product_count"])),
                ("Tổng số lượng bán", str(summary["total_quantity"])),
                ("Tổng doanh thu", format_money(summary["total_amount"])),
            ]
            headers = ["Mã hàng", "Tên hàng", "Đơn vị", "Số lượng", "Doanh thu"]
            column_widths_cm = [3.8, 7.4, 1.8, 2.2, 2.8]
            centered_columns = {0, 2, 3, 4}
        else:
            summary = getattr(self, "_current_goods_summary", {"product_count": 0, "total_quantity": 0, "total_value": 0})
            data_rows = [
                [
                    item["product_code"],
                    item["name"],
                    str(item["quantity"]),
                    format_money(item["sale_price"]),
                ]
                for item in rows
            ]
            file_name = f"bao_cao_ton_kho_{QDate.currentDate().toString('yyyy-MM-dd')}.docx"
            report_title = "BÁO CÁO HÀNG HÓA - SẢN PHẨM TỒN KHO"
            period_label = "Tồn kho hiện tại"
            summary_rows = [
                ("Số sản phẩm", str(summary["product_count"])),
                ("Tổng số lượng tồn", str(summary["total_quantity"])),
                ("Tổng giá trị tồn kho", format_money(summary["total_value"])),
            ]
            headers = ["Mã hàng", "Tên hàng", "Số lượng", "Đơn giá"]
            column_widths_cm = [4.0, 8.5, 2.3, 2.9]
            centered_columns = {0, 2, 3}

        report_path = export_report_docx(
            report_title=report_title,
            period_label=period_label,
            summary_rows=summary_rows,
            headers=headers,
            data_rows=data_rows,
            output_name=file_name,
            column_widths_cm=column_widths_cm,
            centered_columns=centered_columns,
            output_dir=self.invoice_export_dir,
        )
        self._warn_open_export_failure(report_path)

    def _switch_tab(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.menu_buttons):
            if i == idx:
                btn.setStyleSheet(
                    "QPushButton { background: #2563EB; color: white; font-weight: 800; }"
                    "QPushButton:hover { background: #1D4ED8; }"
                )
            else:
                btn.setStyleSheet("")
        self._animate_page(self.stack.currentWidget())

    def _animate_page(self, widget: QWidget) -> None:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(280)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._last_anim = anim

    def _refresh_product_suggestions(self, keyword: str) -> None:
        if self._suspend_product_search:
            return

        self.selected_product_code = None
        self._selected_product_stock = 0
        products = self.order_controller.search_products(keyword)
        self.product_map = {item["product_code"]: item for item in products}
        self.search_product_list.clear()

        if not products:
            self.search_product_list.hide()
            return

        for item in products:
            label = f"{item['product_code']} | {item['name']} | Tồn: {item['quantity']}"
            widget_item = QListWidgetItem(label)
            widget_item.setData(Qt.UserRole, item["product_code"])
            self.search_product_list.addItem(widget_item)

        self.search_product_list.setCurrentRow(0)
        self.search_product_list.setVisible(bool(keyword.strip()))

    def _on_product_suggestion_clicked(self, item: QListWidgetItem) -> None:
        product_code = item.data(Qt.UserRole)
        if product_code:
            self._set_selected_product(str(product_code))

    def _set_selected_product(self, product_code: str) -> None:
        product = self.product_map.get(product_code)
        if not product:
            return
        self.selected_product_code = product_code
        self._selected_product_stock = int(product["quantity"])
        self._suspend_product_search = True
        self.search_product_edit.setText(f"{product['product_code']} | {product['name']}")
        self._suspend_product_search = False
        self.search_product_list.hide()
        self.order_price_spin.setValue(int(product["sale_price"]))
        stock = self._selected_product_stock
        self.order_qty_spin.setMaximum(max(stock, 1))

    def _refresh_customer_suggestions_from_inputs(self) -> None:
        if self._suspend_customer_search:
            return

        name_keyword = self.order_name.text().strip()
        phone_keyword = self.order_phone.text().strip()
        email_keyword = self.order_email.text().strip()
        tax_code_keyword = self.order_tax_code.text().strip()
        keyword = phone_keyword or email_keyword or tax_code_keyword or name_keyword

        self.customer_suggestion_list.clear()
        if not keyword:
            self.customer_suggestion_list.hide()
            return

        customers = self.order_controller.search_customers(keyword)
        if not customers:
            self.customer_suggestion_list.hide()
            return

        for customer in customers:
            label = (
                f"{customer.get('full_name', '')} | {customer.get('phone', '')}"
                f" | {customer.get('email', '')} | {customer.get('tax_code', '')}"
                f" | {customer.get('address', '')}"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, customer)
            self.customer_suggestion_list.addItem(item)

        self.customer_suggestion_list.setCurrentRow(0)
        self.customer_suggestion_list.show()

    def _on_customer_suggestion_clicked(self, item: QListWidgetItem) -> None:
        customer = item.data(Qt.UserRole) or {}
        self._suspend_customer_search = True
        self.order_name.setText(customer.get("full_name", ""))
        self.order_phone.setText(customer.get("phone", ""))
        self.order_address.setText(customer.get("address", ""))
        self.order_email.setText(customer.get("email", ""))
        self.order_tax_code.setText(customer.get("tax_code", ""))
        self._suspend_customer_search = False
        self.customer_suggestion_list.hide()

    def _pick_product_from_input(self) -> bool:
        raw_text = self.search_product_edit.text().strip()
        if not raw_text:
            QMessageBox.information(self, "Thông báo", "Hãy nhập mã hoặc tên sản phẩm")
            return False

        product_code = raw_text.split("|")[0].strip()
        if product_code in self.product_map:
            self._set_selected_product(product_code)
            return True

        matches = self.order_controller.search_products(raw_text)
        if len(matches) == 1:
            self.product_map[matches[0]["product_code"]] = matches[0]
            self._set_selected_product(matches[0]["product_code"])
            return True

        normalized = raw_text.casefold()
        for product in matches:
            if product["product_code"].casefold() == normalized or product["name"].casefold() == normalized:
                self.product_map[product["product_code"]] = product
                self._set_selected_product(product["product_code"])
                return True

        if len(matches) > 1:
            QMessageBox.information(
                self,
                "Cần chọn rõ hơn",
                "Có nhiều sản phẩm phù hợp. Hãy click chọn trong danh sách gợi ý phía dưới.",
            )
            self._refresh_product_suggestions(raw_text)
            return False

        QMessageBox.warning(self, "Không tìm thấy", "Không tìm thấy sản phẩm phù hợp")
        return False

    def _show_selected_product_desc(self) -> None:
        if not self.selected_product_code and not self._pick_product_from_input():
            return
        product = self.product_map.get(self.selected_product_code)
        if not product:
            return
        dlg = DescriptionDialog(
            product_code=product["product_code"],
            product_name=product["name"],
            description=product.get("description", ""),
            parent=self,
        )
        dlg.exec()

    def _append_invoice_line(self) -> None:
        if not self.selected_product_code and not self._pick_product_from_input():
            return
        product = self.product_map.get(self.selected_product_code)
        if not product:
            return

        qty = self.order_qty_spin.value()
        unit_price = self.order_price_spin.value()
        stock = int(product["quantity"])
        if qty > stock:
            QMessageBox.warning(self, "Vượt tồn kho", "Số lượng nhập vượt quá tồn kho hiện tại")
            return

        line = {
            "product_code": product["product_code"],
            "product_name": product["name"],
            "unit": product.get("unit", ""),
            "quantity": qty,
            "unit_price": unit_price,
            "line_total": qty * unit_price,
        }
        self.invoice_lines.append(line)
        self._render_invoice_lines()
        self._update_invoice_totals()
        self._reset_add_item_inputs()

    def _render_invoice_lines(self) -> None:
        self.order_table.setRowCount(len(self.invoice_lines))
        for idx, line in enumerate(self.invoice_lines, 1):
            values = [
                str(idx),
                line["product_code"],
                line["product_name"],
                str(line["quantity"]),
                format_money(line["unit_price"]),
                format_money(line["line_total"]),
            ]
            for col, value in enumerate(values):
                self.order_table.setItem(idx - 1, col, QTableWidgetItem(value))

            delete_btn = QPushButton("Xóa")
            delete_btn.setStyleSheet(
                "QPushButton { background: #FCA5A5; color: #4C1D1D; padding: 6px 10px; }"
                "QPushButton:hover { background: #F87171; color: white; }"
            )
            delete_btn.clicked.connect(lambda checked=False, row=idx - 1: self._remove_invoice_line(row))
            self.order_table.setCellWidget(idx - 1, 6, delete_btn)
        self.order_table.resizeRowsToContents()

    def _remove_invoice_line(self, row: int) -> None:
        if row < 0 or row >= len(self.invoice_lines):
            return
        self.invoice_lines.pop(row)
        self._render_invoice_lines()
        self._update_invoice_totals()

    def _calculate_invoice_totals(self) -> tuple[int, int, int]:
        total_goods = sum(int(line["line_total"]) for line in self.invoice_lines)
        ship_fee = 0
        total_all = total_goods
        return total_goods, ship_fee, total_all

    def _update_invoice_totals(self) -> None:
        _, _, total_all = self._calculate_invoice_totals()
        self.total_all_label.setText(format_money(total_all))

    def _build_order_customer_data(self) -> dict:
        return {
            "full_name": self.order_name.text().strip(),
            "phone": self.order_phone.text().strip(),
            "address": self.order_address.text().strip(),
            "email": self.order_email.text().strip(),
            "tax_code": self.order_tax_code.text().strip(),
            "note": "Tự động cập nhật từ lên đơn",
        }

    def _build_order_document_data(self, invoice_no: str = "") -> tuple[dict, dict, list[dict]]:
        if not self.invoice_lines:
            raise ValueError("Đơn hàng phải có ít nhất 1 sản phẩm")

        customer_data = self._build_order_customer_data()
        if not customer_data["full_name"]:
            raise ValueError("Họ tên khách hàng không được để trống")

        created_at = self.order_created_at.text().strip() or now_iso_utc7()
        total_goods, ship_fee, total_all = self._calculate_invoice_totals()
        export_lines = [dict(line) for line in self.invoice_lines]
        document_data = {
            "invoice_no": invoice_no,
            "created_at": created_at,
            "customer_name": customer_data["full_name"],
            "phone": customer_data["phone"],
            "email": customer_data["email"],
            "tax_code": customer_data["tax_code"],
            "address": customer_data["address"],
            "goods_amount": total_goods,
            "ship_fee": ship_fee,
            "total_amount": total_all,
        }
        return customer_data, document_data, export_lines

    def _show_document_preview(
        self,
        document_data: dict,
        items: list[dict],
        document_kind: str,
        *,
        show_confirm: bool = True,
        confirm_text: str | None = None,
        window_title: str | None = None,
        hint_text: str | None = None,
    ) -> bool:
        preview_dialog = InvoicePreviewDialog(
            document_data,
            items,
            self,
            document_kind=document_kind,
            show_confirm=show_confirm,
            confirm_text=confirm_text,
            window_title=window_title,
            hint_text=hint_text,
        )
        preview_dialog.exec()
        return preview_dialog.confirmed

    def _reset_add_item_inputs(self) -> None:
        self.search_product_edit.clear()
        self.search_product_list.clear()
        self.search_product_list.hide()
        self.selected_product_code = None
        self._selected_product_stock = 0
        self.order_qty_spin.setMaximum(1_000_000_000)
        self.order_qty_spin.setValue(1)
        self.order_price_spin.setValue(0)
        self.search_product_edit.setFocus()

    def _set_order_editing_state(self, quotation_id: int | None, export_path: str = "") -> None:
        self._editing_quotation_id = quotation_id
        self._editing_quotation_export_path = export_path
        if quotation_id is None:
            self.save_quote_btn.setText("Lưu bản báo giá")
            self.export_btn.setText("Xuất hóa đơn")
            return
        self.save_quote_btn.setText("Cập nhật bản báo giá")
        self.export_btn.setText("Xuất hóa đơn từ báo giá")

    def _reset_order_form(self) -> None:
        self._set_order_editing_state(None)
        self._order_created_at_override = None
        self.invoice_lines.clear()
        self._render_invoice_lines()
        self._update_invoice_totals()
        self.order_name.clear()
        self.order_phone.clear()
        self.order_address.clear()
        self.order_email.clear()
        self.order_tax_code.clear()
        self.customer_suggestion_list.clear()
        self.customer_suggestion_list.hide()
        self._reset_add_item_inputs()

    def _remove_exported_file(self, export_path: Path) -> None:
        try:
            if export_path.exists():
                export_path.unlink()
        except OSError:
            pass

    def _open_exported_document(self, export_path: Path) -> str | None:
        try:
            resolved_path = export_path.resolve()
        except OSError:
            resolved_path = export_path

        if QDesktopServices.openUrl(QUrl.fromLocalFile(str(resolved_path))):
            return None

        return (
            "Đã xuất file nhưng không thể mở tự động bằng ứng dụng mặc định.\n"
            f"Bạn có thể mở thủ công tại:\n{resolved_path}"
        )

    def _warn_open_export_failure(self, export_path: Path) -> None:
        open_error = self._open_exported_document(export_path)
        if open_error:
            QMessageBox.warning(self, "Không thể mở file tự động", open_error)

    def _save_quotation(self) -> None:
        quotation_id: int | None = None
        created_new_quotation = False
        try:
            customer_data, quotation_data, export_lines = self._build_order_document_data()
            confirmed = self._show_document_preview(
                quotation_data,
                export_lines,
                "quotation",
                confirm_text="Cập nhật bản báo giá" if self._editing_quotation_id is not None else "Lưu bản báo giá",
            )
            if not confirmed:
                return

            old_export_path = self._editing_quotation_export_path
            if self._editing_quotation_id is None:
                quotation_id = self.order_controller.create_quotation(customer_data, quotation_data, export_lines)
                created_new_quotation = True
            else:
                quotation_id = self._editing_quotation_id
                self.order_controller.update_quotation(quotation_id, customer_data, quotation_data, export_lines)

            output_name = build_quotation_output_name(customer_data["full_name"], quotation_data["created_at"])
            export_path = export_invoice_docx(
                quotation_data,
                export_lines,
                self.invoice_export_dir,
                document_kind="quotation",
                output_name=output_name,
            )
            self.order_controller.update_quotation_export_path(quotation_id, str(export_path))
            if old_export_path and old_export_path != str(export_path):
                self._remove_exported_file(Path(old_export_path))

            self._warn_open_export_failure(export_path)
            self._reset_order_form()
            self.refresh_products()
            self.refresh_report()
        except Exception as exc:  # pragma: no cover - dialog feedback
            if created_new_quotation and quotation_id is not None:
                try:
                    self.order_controller.cancel_quotation(quotation_id)
                except Exception:
                    pass
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _open_recent_quotations(self) -> None:
        dialog = RecentQuotationsDialog(
            load_rows=lambda: self.order_controller.list_recent_quotations(100),
            on_edit=self._edit_quotation_from_dialog,
            on_export=self._export_quotation_from_dialog,
            on_cancel=self._cancel_quotation_from_dialog,
            parent=self,
        )
        dialog.exec()

    def _edit_quotation_from_dialog(self, quotation_id: int) -> bool:
        detail = self.order_controller.get_quotation_detail(quotation_id)
        if not detail:
            QMessageBox.warning(self, "Không tìm thấy", "Không lấy được chi tiết bản báo giá")
            return False

        quotation = detail["quotation"]
        items = detail["items"]

        self._set_order_editing_state(quotation_id, str(quotation.get("export_path", "") or ""))
        self._order_created_at_override = str(quotation.get("created_at", "") or now_iso_utc7())

        self._suspend_customer_search = True
        self.order_name.setText(str(quotation.get("customer_name", "") or ""))
        self.order_phone.setText(str(quotation.get("phone", "") or ""))
        self.order_address.setText(str(quotation.get("address", "") or ""))
        self.order_email.setText(str(quotation.get("email", "") or ""))
        self.order_tax_code.setText(str(quotation.get("tax_code", "") or ""))
        self._suspend_customer_search = False

        self.customer_suggestion_list.clear()
        self.customer_suggestion_list.hide()
        self.invoice_lines = [
            {
                "product_code": str(item.get("product_code", "") or ""),
                "product_name": str(item.get("product_name", "") or ""),
                "unit": str(item.get("unit", "") or ""),
                "quantity": int(item.get("quantity", 0) or 0),
                "unit_price": int(item.get("unit_price", 0) or 0),
                "line_total": int(item.get("line_total", 0) or 0),
            }
            for item in items
        ]
        self._render_invoice_lines()
        self._update_invoice_totals()
        self._reset_add_item_inputs()
        self._switch_tab(0)
        self._refresh_clock()
        return True

    def _view_quotation_preview(self, quotation_id: int) -> None:
        detail = self.order_controller.get_quotation_detail(quotation_id)
        if not detail:
            QMessageBox.warning(self, "Không tìm thấy", "Không lấy được chi tiết bản báo giá")
            return

        quotation = detail["quotation"]
        preview_data = {
            "invoice_no": "",
            "created_at": quotation["created_at"],
            "customer_name": quotation["customer_name"],
            "phone": quotation.get("phone", ""),
            "email": quotation.get("email", ""),
            "tax_code": quotation.get("tax_code", ""),
            "address": quotation.get("address", ""),
            "goods_amount": int(quotation.get("goods_amount", 0)),
            "ship_fee": int(quotation.get("ship_fee", 0)),
            "total_amount": int(quotation.get("total_amount", 0)),
        }
        preview_dialog = InvoicePreviewDialog(
            preview_data,
            detail["items"],
            self,
            document_kind="quotation",
            show_confirm=False,
            window_title="Xem trước bản báo giá A4",
            hint_text="Hiển thị toàn bộ nội dung bản báo giá trên khổ giấy A4",
        )
        preview_dialog.exec()

    def _export_quotation_from_dialog(self, quotation_id: int) -> bool:
        detail = self.order_controller.get_quotation_detail(quotation_id)
        if not detail:
            QMessageBox.warning(self, "Không tìm thấy", "Không lấy được chi tiết bản báo giá")
            return False

        quotation = detail["quotation"]
        items = detail["items"]
        invoice_no = self.order_controller.generate_invoice_no()
        invoice_data = {
            "invoice_no": invoice_no,
            "created_at": quotation["created_at"],
            "customer_name": quotation["customer_name"],
            "phone": quotation.get("phone", ""),
            "email": quotation.get("email", ""),
            "tax_code": quotation.get("tax_code", ""),
            "address": quotation.get("address", ""),
            "goods_amount": int(quotation.get("goods_amount", 0)),
            "ship_fee": int(quotation.get("ship_fee", 0)),
            "total_amount": int(quotation.get("total_amount", 0)),
        }

        if not self._show_document_preview(
            invoice_data,
            items,
            "invoice",
            confirm_text="Xuất hóa đơn",
        ):
            return False

        try:
            export_path = export_invoice_docx(
                invoice_data,
                items,
                self.invoice_export_dir,
                document_kind="invoice",
                output_name=build_invoice_output_name(invoice_no, quotation.get("customer_name", "")),
            )
            try:
                self.order_controller.export_quotation_to_invoice(quotation_id, invoice_no)
            except Exception:
                self._remove_exported_file(export_path)
                raise

            self._warn_open_export_failure(export_path)
            self.refresh_products()
            self.refresh_report()
            return True
        except Exception as exc:  # pragma: no cover - dialog feedback
            QMessageBox.critical(self, "Lỗi", str(exc))
            return False

    def _cancel_quotation_from_dialog(self, quotation_id: int) -> bool:
        answer = QMessageBox.question(
            self,
            "Hủy đơn",
            "Hủy toàn bộ bản báo giá này và xóa khỏi danh sách?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return False

        try:
            self.order_controller.cancel_quotation(quotation_id)
            QMessageBox.information(self, "Đã hủy", "Bản báo giá đã được hủy hoàn toàn")
            return True
        except Exception as exc:  # pragma: no cover - dialog feedback
            QMessageBox.critical(self, "Lỗi", str(exc))
            return False

    def _export_invoice(self) -> None:
        try:
            invoice_no = self.order_controller.generate_invoice_no()
            customer_data, invoice_data, export_lines = self._build_order_document_data(invoice_no=invoice_no)
            if not self._show_document_preview(invoice_data, export_lines, "invoice"):
                return

            export_path = export_invoice_docx(
                invoice_data,
                export_lines,
                self.invoice_export_dir,
                document_kind="invoice",
                output_name=build_invoice_output_name(invoice_no, customer_data.get("full_name", "")),
            )
            try:
                if self._editing_quotation_id is None:
                    self.order_controller.create_invoice(customer_data, invoice_data, export_lines)
                else:
                    self.order_controller.update_quotation(
                        self._editing_quotation_id,
                        customer_data,
                        invoice_data,
                        export_lines,
                    )
                    self.order_controller.export_quotation_to_invoice(self._editing_quotation_id, invoice_no)
            except Exception:
                self._remove_exported_file(export_path)
                raise

            self._warn_open_export_failure(export_path)
            self._reset_order_form()
            self.refresh_products()
            self.refresh_report()
        except Exception as exc:  # pragma: no cover - dialog feedback
            QMessageBox.critical(self, "Lỗi", str(exc))

    def refresh_products(self) -> None:
        products = self.product_controller.list_products()
        self.product_map = {item["product_code"]: item for item in products}

        self.product_table.setRowCount(len(products))
        for row, product in enumerate(products):
            base_values = [
                product["product_code"],
                product["name"],
                str(product["quantity"]),
                format_money(product["sale_price"]),
                "Xem thêm",
                product["updated_at"],
            ]
            for col, value in enumerate(base_values):
                if col == 4:
                    btn = QPushButton("Xem thêm")
                    btn.clicked.connect(
                        lambda checked=False, p=product: self._show_product_desc_direct(p)
                    )
                    self.product_table.setCellWidget(row, col, btn)
                else:
                    self.product_table.setItem(row, col, QTableWidgetItem(value))
        self.product_table.resizeRowsToContents()

    def _show_product_desc_direct(self, product: dict) -> None:
        dlg = DescriptionDialog(
            product_code=product["product_code"],
            product_name=product["name"],
            description=product.get("description", ""),
            parent=self,
        )
        dlg.exec()

    def _selected_product_code(self) -> str | None:
        selected = self.product_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        code_item = self.product_table.item(row, 0)
        return code_item.text() if code_item else None

    def _sync_product_action_state(self) -> None:
        has_selection = self._selected_product_code() is not None
        self.btn_edit_product.setEnabled(has_selection)
        self.btn_product_history.setEnabled(has_selection)
        self.btn_delete_product.setEnabled(has_selection)

    def _on_view_product_history(self) -> None:
        code = self._selected_product_code()
        if not code:
            QMessageBox.information(self, "Thông báo", "Hãy chọn sản phẩm để xem lịch sử")
            return

        product = self.product_map.get(code)
        if not product:
            QMessageBox.warning(self, "Không tìm thấy", "Sản phẩm đã chọn không tồn tại")
            return

        history_rows = self.product_controller.list_product_update_history(code)
        dialog = ProductHistoryDialog(product, history_rows, self)
        dialog.exec()

    def _on_add_product(self) -> None:
        if not PasswordDialog.verify(self, "Xác thực thêm sản phẩm"):
            return
        dlg = ProductFormDialog(
            self,
            mode="add",
            import_loader=self.product_controller.parse_product_import_file,
            template_exporter=self.product_controller.export_product_import_template,
        )
        if dlg.exec() != ProductFormDialog.Accepted:
            return
        try:
            imported_payloads = dlg.imported_payloads()
            if imported_payloads:
                self.product_controller.create_products(imported_payloads)
            else:
                self.product_controller.create_product(dlg.payload())
            self.refresh_products()
            message = "Đã thêm sản phẩm thành công"
            missing_code_count = dlg.missing_code_count()
            if missing_code_count > 0:
                message += f"\nCó {missing_code_count} sản phẩm không có Mã sản phẩm."
            QMessageBox.information(self, "Thành công", message)
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_edit_product(self) -> None:
        code = self._selected_product_code()
        if not code:
            return
        if not PasswordDialog.verify(self, "Xác thực sửa thông tin"):
            return

        product = self.product_map.get(code)
        if not product:
            QMessageBox.warning(self, "Không tìm thấy", "Sản phẩm đã chọn không tồn tại")
            return

        dlg = ProductFormDialog(self, mode="edit", initial=product)
        if dlg.exec() != ProductFormDialog.Accepted:
            return

        try:
            self.product_controller.update_product(code, dlg.payload())
            self.refresh_products()
            QMessageBox.information(self, "Thành công", "Đã cập nhật sản phẩm")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _on_delete_product(self) -> None:
        code = self._selected_product_code()
        if not code:
            return

        if not PasswordDialog.verify(self, "Xác thực xóa sản phẩm"):
            return

        ok = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa sản phẩm mã {code}?",
        )
        if ok != QMessageBox.Yes:
            return

        if not PasswordDialog.verify(self, "Nhập lại mật khẩu để xác nhận xóa"):
            return

        try:
            self.product_controller.delete_product(code)
            self.refresh_products()
            QMessageBox.information(self, "Thành công", "Đã xóa sản phẩm")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def refresh_report(self) -> None:
        revenue_period_type, revenue_period_value = self._selected_period(
            self.revenue_period_type_combo,
            self.revenue_period_edit,
        )
        revenue_label = self._period_label(revenue_period_type, revenue_period_value)
        revenue_report = self.report_controller.revenue_report(revenue_period_type, revenue_period_value)
        self._current_revenue_period_type = revenue_period_type
        self._current_revenue_period_value = revenue_period_value
        self._current_revenue_rows = revenue_report["rows"]
        self._current_revenue_summary = revenue_report

        self._set_metric_card_value(
            self.revenue_total_card,
            format_money(revenue_report["total_amount"]),
            "",
        )
        self._set_metric_card_value(
            self.revenue_count_card,
            str(revenue_report["invoice_count"]),
            "",
        )

        goods_report_type = str(self.goods_report_type_combo.currentData() or "sold")
        self._current_goods_report_type = goods_report_type

        if goods_report_type == "sold":
            goods_period_type, goods_period_value = self._selected_period(
                self.goods_period_type_combo,
                self.goods_period_edit,
            )
            goods_label = self._period_label(goods_period_type, goods_period_value)
            goods_report = self.report_controller.sold_products_report(goods_period_type, goods_period_value)
            self._current_goods_period_type = goods_period_type
            self._current_goods_period_value = goods_period_value
            self._current_goods_rows = goods_report["rows"]
            self._current_goods_summary = goods_report

            self._set_metric_card_value(
                self.goods_primary_card,
                str(goods_report["total_quantity"]),
                "",
            )
            self._set_metric_card_value(
                self.goods_secondary_card,
                format_money(goods_report["total_amount"]),
                "",
            )
        else:
            stock_report = self.report_controller.stock_products_report()
            self._current_goods_rows = stock_report["rows"]
            self._current_goods_summary = stock_report
            self._current_goods_period_type = ""
            self._current_goods_period_value = ""

            self._set_metric_card_value(
                self.goods_primary_card,
                str(stock_report["total_quantity"]),
                "",
            )
            self._set_metric_card_value(
                self.goods_secondary_card,
                format_money(stock_report["total_value"]),
                "",
            )

        self._refresh_invoice_search_results(self.invoice_search_edit.text())

    def _selected_invoice_no(self) -> str | None:
        if getattr(self, "invoice_table", None) is None:
            return None
        selected = self.invoice_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        invoice_item = self.invoice_table.item(row, 0)
        return invoice_item.text() if invoice_item else None

    def _sync_invoice_action_state(self) -> None:
        has_selected_invoice = self._selected_invoice_no() is not None
        if getattr(self, "view_invoice_detail_btn", None) is not None:
            self.view_invoice_detail_btn.setEnabled(has_selected_invoice)
        if getattr(self, "export_selected_invoice_btn", None) is not None:
            self.export_selected_invoice_btn.setEnabled(has_selected_invoice)

    def _load_invoice_export_dir(self) -> Path:
        stored_path = self._settings.value("invoice_export_dir", str(EXPORT_DIR), type=str)
        export_dir = Path(stored_path).expanduser()
        return export_dir

    def _update_invoice_export_dir_label(self) -> None:
        if getattr(self, "export_dir_label", None) is not None:
            self.export_dir_label.setText(str(self.invoice_export_dir))
        if getattr(self, "report_export_dir_label", None) is not None:
            self.report_export_dir_label.setText(str(self.invoice_export_dir))

    def _choose_invoice_export_dir(self) -> None:
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Chọn nơi lưu file hóa đơn",
            str(self.invoice_export_dir),
        )
        if not selected_dir:
            return

        self.invoice_export_dir = Path(selected_dir)
        self._settings.setValue("invoice_export_dir", str(self.invoice_export_dir))
        self._update_invoice_export_dir_label()

    def _export_selected_invoice_docx(self) -> None:
        invoice_no = self._selected_invoice_no()
        if not invoice_no:
            return

        detail = self.order_controller.get_invoice_detail(invoice_no)
        if not detail:
            QMessageBox.warning(self, "Không tìm thấy", "Không lấy được chi tiết hóa đơn")
            return

        try:
            preview_dialog = InvoicePreviewDialog(detail["invoice"], detail["items"], self, document_kind="invoice")
            preview_dialog.exec()
            if not preview_dialog.confirmed:
                return

            export_path = export_invoice_docx(
                detail["invoice"],
                detail["items"],
                self.invoice_export_dir,
                document_kind="invoice",
                output_name=build_invoice_output_name(invoice_no, detail["invoice"].get("customer_name", "")),
            )
            self._warn_open_export_failure(export_path)
        except Exception as exc:  # pragma: no cover - dialog feedback
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _show_selected_invoice_detail(self) -> None:
        invoice_no = self._selected_invoice_no()
        if not invoice_no:
            return
        detail = self.order_controller.get_invoice_detail(invoice_no)
        if not detail:
            QMessageBox.warning(self, "Không tìm thấy", "Không lấy được chi tiết hóa đơn")
            return
        dialog = InvoiceDetailDialog(detail, self)
        dialog.exec()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_font_by_window_size()
        self._sync_order_table_widths()

    def _sync_order_table_widths(self) -> None:
        if getattr(self, "order_table", None) is None:
            return

        self.order_table.setColumnWidth(0, 56)
        self.order_table.setColumnWidth(1, 220)
        self.order_table.setColumnWidth(3, 96)
        self.order_table.setColumnWidth(4, 130)
        self.order_table.setColumnWidth(5, 150)
        self.order_table.setColumnWidth(6, 88)

    def _apply_payment_summary_fonts(self) -> None:
        app = QApplication.instance()
        base_font = app.font() if app is not None else QFont("Times New Roman")
        base_px = base_font.pixelSize() if base_font.pixelSize() > 0 else 14

        group_font = QFont(base_font)
        group_font.setPixelSize(base_px + 2)
        group_font.setBold(True)
        if getattr(self, "payment_box", None) is not None:
            self.payment_box.setFont(group_font)

        label_font = QFont(base_font)
        label_font.setPixelSize(base_px + 2)
        label_font.setBold(True)

        amount_font = QFont(base_font)
        amount_font.setPixelSize(base_px + 4)
        amount_font.setBold(True)

        if getattr(self, "total_all_text_label", None) is not None:
            self.total_all_text_label.setFont(label_font)
        if getattr(self, "total_all_label", None) is not None:
            self.total_all_label.setFont(amount_font)

        export_box_font = QFont(base_font)
        export_box_font.setPixelSize(base_px + 1)
        export_box_font.setBold(True)
        if getattr(self, "export_location_box", None) is not None:
            self.export_location_box.setFont(export_box_font)

    def _sync_font_by_window_size(self) -> None:
        width_factor = self.width() / 72
        height_factor = self.height() / 48
        px = max(MIN_FONT_PX, int(min(width_factor, height_factor)))

        app = QApplication.instance()
        if app is None:
            return
        font = QFont("Times New Roman")
        font.setPixelSize(px)
        app.setFont(font)

        self._apply_payment_summary_fonts()

        export_font = QFont(font)
        export_font.setPixelSize(px + 2)
        if getattr(self, "export_btn", None) is not None:
            self.export_btn.setFont(export_font)

        menu_font = QFont(font)
        menu_font.setPixelSize(px + 3)
        for button in self.menu_buttons:
            button.setFont(menu_font)
