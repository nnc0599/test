from __future__ import annotations

from typing import Any

from pathlib import Path

from PySide6.QtCore import QEvent, QEasingCurve, QPropertyAnimation, QSettings, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
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
from app.utils.invoice_docx import export_invoice_docx
from app.views.dialogs.auth_dialog import PasswordDialog
from app.views.dialogs.description_dialog import DescriptionDialog
from app.views.dialogs.invoice_detail_dialog import InvoiceDetailDialog
from app.views.dialogs.invoice_preview_dialog import InvoicePreviewDialog
from app.views.dialogs.product_history_dialog import ProductHistoryDialog
from app.views.dialogs.product_dialog import ProductFormDialog


def format_money(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


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
        self.search_product_list.hide()

        self.select_product_btn = QPushButton("Chọn sản phẩm")
        self.select_product_btn.clicked.connect(self._pick_product_from_input)

        self.order_qty_spin = QSpinBox()
        self.order_qty_spin.setRange(1, 1_000_000_000)
        self.order_qty_hint = QLabel("Tồn hiện tại: chưa chọn sản phẩm")
        self.order_qty_hint.setStyleSheet("color: #475569; font-style: italic;")
        self.order_price_spin = QSpinBox()
        self.order_price_spin.setRange(0, 2_000_000_000)

        self.add_line_btn = QPushButton("Thêm vào danh sách")
        self.add_line_btn.clicked.connect(self._append_invoice_line)

        add_grid.addWidget(QLabel("Tìm kiếm sản phẩm"), 0, 0)
        add_grid.addWidget(self.search_product_edit, 0, 1, 1, 2)
        add_grid.addWidget(self.select_product_btn, 0, 3)
        add_grid.addWidget(QLabel("Số lượng"), 0, 4)
        add_grid.addWidget(self.order_qty_spin, 0, 5)
        add_grid.addWidget(QLabel("Đơn giá"), 0, 6)
        add_grid.addWidget(self.order_price_spin, 0, 7)
        add_grid.addWidget(self.add_line_btn, 0, 8)
        add_grid.addWidget(self.search_product_list, 1, 1, 1, 3)
        add_grid.addWidget(self.order_qty_hint, 1, 4, 1, 5)

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

        payment_box = QGroupBox("Tổng tiền hóa đơn")
        payment_form = QFormLayout(payment_box)

        self.total_goods_text_label = QLabel("Tổng tiền hàng")
        self.total_goods_label = QLabel("0")
        self.ship_fee_spin = QSpinBox()
        self.ship_fee_spin.setRange(0, 2_000_000_000)
        self.ship_fee_spin.setValue(0)
        self.total_all_label = QLabel("0")

        payment_form.addRow(self.total_goods_text_label, self.total_goods_label)
        payment_form.addRow("Phí ship", self.ship_fee_spin)
        payment_form.addRow("Tổng số tiền", self.total_all_label)

        layout.addWidget(payment_box)

        export_location_box = QGroupBox("Nơi lưu file hóa đơn")
        export_location_layout = QHBoxLayout(export_location_box)
        self.export_dir_label = QLabel(str(self.invoice_export_dir))
        self.export_dir_label.setWordWrap(True)
        self.choose_export_dir_btn = QPushButton("Chọn nơi lưu file")
        self.choose_export_dir_btn.clicked.connect(self._choose_invoice_export_dir)
        export_location_layout.addWidget(self.export_dir_label, 1)
        export_location_layout.addWidget(self.choose_export_dir_btn)
        layout.addWidget(export_location_box)

        self.export_btn = QPushButton("XUẤT HÓA ĐƠN")
        self.export_btn.setMinimumHeight(58)
        self.export_btn.setStyleSheet(
            "QPushButton { background: #0EA5E9; color: white; font-weight: 800; }"
            "QPushButton:hover { background: #0284C7; }"
            "QPushButton:pressed { background: #0369A1; }"
        )
        self.export_btn.clicked.connect(self._export_invoice)
        layout.addWidget(self.export_btn)

        self.search_product_edit.textChanged.connect(self._refresh_product_suggestions)
        self.search_product_edit.returnPressed.connect(self._pick_product_from_input)
        self.search_product_list.itemClicked.connect(self._on_product_suggestion_clicked)
        self.order_qty_spin.valueChanged.connect(self._update_quantity_hint)
        self.ship_fee_spin.valueChanged.connect(self._update_invoice_totals)
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
            for widget in [self.search_product_list, self.search_product_edit, self.select_product_btn]
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
        layout.setSpacing(10)

        cards = QHBoxLayout()
        self.today_card = self._build_card("Doanh thu hôm nay")
        self.month_card = self._build_card("Doanh thu tháng")
        cards.addWidget(self.today_card)
        cards.addWidget(self.month_card)
        layout.addLayout(cards)

        panel = QHBoxLayout()

        self.day_table = QTableWidget(0, 2)
        self.day_table.setHorizontalHeaderLabels(["Ngày", "Doanh thu"])
        self.day_table.verticalHeader().setVisible(False)
        self.day_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.day_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.day_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        self.month_table = QTableWidget(0, 2)
        self.month_table.setHorizontalHeaderLabels(["Tháng", "Doanh thu"])
        self.month_table.verticalHeader().setVisible(False)
        self.month_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.month_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.month_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        day_group = QGroupBox("Thống kê theo ngày")
        day_layout = QVBoxLayout(day_group)
        day_layout.addWidget(self.day_table)

        month_group = QGroupBox("Thống kê theo tháng")
        month_layout = QVBoxLayout(month_group)
        month_layout.addWidget(self.month_table)

        panel.addWidget(day_group)
        panel.addWidget(month_group)
        layout.addLayout(panel)

        refresh_btn = QPushButton("Làm mới báo cáo")
        refresh_btn.clicked.connect(self.refresh_report)
        layout.addWidget(refresh_btn)

        management_panel = QHBoxLayout()

        customer_group = QGroupBox("Khách hàng đã lưu")
        customer_layout = QVBoxLayout(customer_group)
        self.customer_table = QTableWidget(0, 6)
        self.customer_table.setHorizontalHeaderLabels(
            ["Họ tên", "Số điện thoại", "Gmail", "Mã số thuế", "Địa chỉ", "Ghi chú"]
        )
        self.customer_table.verticalHeader().setVisible(False)
        self.customer_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.customer_table.setSelectionBehavior(QTableWidget.SelectRows)
        customer_header = self.customer_table.horizontalHeader()
        customer_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        customer_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        customer_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        customer_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        customer_header.setSectionResizeMode(4, QHeaderView.Stretch)
        customer_header.setSectionResizeMode(5, QHeaderView.Stretch)
        customer_layout.addWidget(self.customer_table)

        invoice_group = QGroupBox("Danh sách hóa đơn")
        invoice_layout = QVBoxLayout(invoice_group)
        self.invoice_table = QTableWidget(0, 9)
        self.invoice_table.setHorizontalHeaderLabels(
            [
                "Số hóa đơn",
                "Ngày tạo",
                "Khách hàng",
                "Số điện thoại",
                "Gmail",
                "Mã số thuế",
                "Địa chỉ",
                "Tổng tiền",
                "Số dòng",
            ]
        )
        self.invoice_table.verticalHeader().setVisible(False)
        self.invoice_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.invoice_table.setSelectionBehavior(QTableWidget.SelectRows)
        invoice_header = self.invoice_table.horizontalHeader()
        invoice_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(6, QHeaderView.Stretch)
        invoice_header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        invoice_header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        invoice_layout.addWidget(self.invoice_table)

        invoice_actions = QHBoxLayout()

        self.view_invoice_detail_btn = QPushButton("Xem chi tiết hóa đơn")
        self.view_invoice_detail_btn.setEnabled(False)
        self.view_invoice_detail_btn.clicked.connect(self._show_selected_invoice_detail)
        invoice_actions.addWidget(self.view_invoice_detail_btn)

        self.export_selected_invoice_btn = QPushButton("Xuất lại file Word")
        self.export_selected_invoice_btn.setEnabled(False)
        self.export_selected_invoice_btn.clicked.connect(self._export_selected_invoice_docx)
        invoice_actions.addWidget(self.export_selected_invoice_btn)

        self.report_export_dir_label = QLabel(str(self.invoice_export_dir))
        self.report_export_dir_label.setWordWrap(True)
        invoice_actions.addWidget(self.report_export_dir_label, 1)

        self.choose_export_dir_from_list_btn = QPushButton("Chọn nơi lưu file")
        self.choose_export_dir_from_list_btn.clicked.connect(self._choose_invoice_export_dir)
        invoice_actions.addWidget(self.choose_export_dir_from_list_btn)

        self.invoice_table.itemSelectionChanged.connect(self._sync_invoice_action_state)
        self.invoice_table.itemDoubleClicked.connect(lambda _item: self._show_selected_invoice_detail())
        invoice_layout.addLayout(invoice_actions)

        management_panel.addWidget(customer_group)
        management_panel.addWidget(invoice_group)
        layout.addLayout(management_panel)

        return page

    def _build_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #1D4ED8, stop:1 #0EA5E9); border-radius: 14px; }"
            "QLabel { background: transparent; color: white; }"
        )
        card_layout = QVBoxLayout(card)
        title_label = QLabel(title)
        value_label = QLabel("0")
        value_label.setProperty("cardValue", True)
        value_label.setAlignment(Qt.AlignRight)
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card_layout.addStretch()
        card.value_label = value_label  # type: ignore[attr-defined]
        return card

    def _bind_runtime_clock(self) -> None:
        self._refresh_clock()
        timer = QTimer(self)
        timer.setInterval(1000)
        timer.timeout.connect(self._refresh_clock)
        timer.start()
        self._clock_timer = timer

    def _refresh_clock(self) -> None:
        self.order_created_at.setText(now_iso_utc7())

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
        self._update_quantity_hint()
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
        self.order_qty_spin.setToolTip(f"Số lượng tồn: {stock}")
        self._update_quantity_hint()

    def _update_quantity_hint(self) -> None:
        if not self.selected_product_code:
            self.order_qty_hint.setText("Tồn hiện tại: chưa chọn sản phẩm")
            self.order_qty_hint.setStyleSheet("color: #475569; font-style: italic;")
            return

        remaining = self._selected_product_stock - self.order_qty_spin.value()
        if remaining >= 0:
            self.order_qty_hint.setText(
                f"Tồn hiện tại: {self._selected_product_stock} | Còn lại sau khi thêm: {remaining}"
            )
            self.order_qty_hint.setStyleSheet("color: #475569; font-style: italic;")
        else:
            self.order_qty_hint.setText(
                f"Tồn hiện tại: {self._selected_product_stock} | Vượt tồn: {abs(remaining)}"
            )
            self.order_qty_hint.setStyleSheet("color: #B91C1C; font-style: italic;")

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

    def _remove_invoice_line(self, row: int) -> None:
        if row < 0 or row >= len(self.invoice_lines):
            return
        self.invoice_lines.pop(row)
        self._render_invoice_lines()
        self._update_invoice_totals()

    def _calculate_invoice_totals(self) -> tuple[int, int, int]:
        total_goods = sum(int(line["line_total"]) for line in self.invoice_lines)
        ship_fee = self.ship_fee_spin.value()
        total_all = total_goods + ship_fee
        return total_goods, ship_fee, total_all

    def _update_invoice_totals(self) -> None:
        total_goods, _, total_all = self._calculate_invoice_totals()
        self.total_goods_label.setText(format_money(total_goods))
        self.total_all_label.setText(format_money(total_all))

    def _export_invoice(self) -> None:
        try:
            created_at = self.order_created_at.text().strip() or now_iso_utc7()
            invoice_no = self.order_controller.generate_invoice_no()
            total_goods, ship_fee, total_all = self._calculate_invoice_totals()
            export_lines = [dict(line) for line in self.invoice_lines]

            customer_data = {
                "full_name": self.order_name.text().strip(),
                "phone": self.order_phone.text().strip(),
                "address": self.order_address.text().strip(),
                "email": self.order_email.text().strip(),
                "tax_code": self.order_tax_code.text().strip(),
                "note": "Tự động cập nhật từ lên đơn",
            }
            invoice_data = {
                "invoice_no": invoice_no,
                "created_at": created_at,
                "goods_amount": total_goods,
                "ship_fee": ship_fee,
                "total_amount": total_all,
                "paid_amount": 0,
                "payment_date": created_at,
            }

            preview_invoice = {
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

            preview_dialog = InvoicePreviewDialog(preview_invoice, export_lines, self)
            preview_dialog.exec()
            if not preview_dialog.confirmed:
                return

            self.order_controller.create_invoice(customer_data, invoice_data, self.invoice_lines)

            export_path = export_invoice_docx(
                preview_invoice,
                export_lines,
                self.invoice_export_dir,
            )

            QMessageBox.information(
                self,
                "Thành công",
                f"Đã xuất hóa đơn {invoice_no}\nFile Word: {export_path}",
            )
            self.invoice_lines.clear()
            self._render_invoice_lines()
            self._update_invoice_totals()
            self.order_name.clear()
            self.order_phone.clear()
            self.order_address.clear()
            self.order_email.clear()
            self.order_tax_code.clear()
            self.search_product_edit.clear()
            self.search_product_list.clear()
            self.search_product_list.hide()
            self.customer_suggestion_list.clear()
            self.customer_suggestion_list.hide()
            self.selected_product_code = None
            self._selected_product_stock = 0
            self.ship_fee_spin.setValue(0)
            self.order_price_spin.setValue(0)
            self.order_qty_spin.setValue(1)
            self._update_quantity_hint()
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
        dlg = ProductFormDialog(self, mode="add")
        if dlg.exec() != ProductFormDialog.Accepted:
            return
        try:
            self.product_controller.create_product(dlg.payload())
            self.refresh_products()
            QMessageBox.information(self, "Thành công", "Đã thêm sản phẩm mới")
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
        summary = self.report_controller.summary()
        self.today_card.value_label.setText(format_money(summary["today"]))  # type: ignore[attr-defined]
        self.month_card.value_label.setText(format_money(summary["month"]))  # type: ignore[attr-defined]

        by_day = self.report_controller.by_day()
        by_month = self.report_controller.by_month()

        self.day_table.setRowCount(len(by_day))
        for row, item in enumerate(by_day):
            self.day_table.setItem(row, 0, QTableWidgetItem(item["day"]))
            self.day_table.setItem(row, 1, QTableWidgetItem(format_money(item["total"])))

        self.month_table.setRowCount(len(by_month))
        for row, item in enumerate(by_month):
            self.month_table.setItem(row, 0, QTableWidgetItem(item["month"]))
            self.month_table.setItem(row, 1, QTableWidgetItem(format_money(item["total"])))

        customers = self.order_controller.list_customers()
        self.customer_table.setRowCount(len(customers))
        for row, customer in enumerate(customers):
            values = [
                customer.get("full_name", ""),
                customer.get("phone", ""),
                customer.get("email", ""),
                customer.get("tax_code", ""),
                customer.get("address", ""),
                customer.get("note", ""),
            ]
            for col, value in enumerate(values):
                self.customer_table.setItem(row, col, QTableWidgetItem(value))

        invoices = self.order_controller.list_invoices()
        self.invoice_table.setRowCount(len(invoices))
        for row, invoice in enumerate(invoices):
            values = [
                invoice["invoice_no"],
                invoice["created_at"],
                invoice["customer_name"],
                invoice.get("phone", ""),
                invoice.get("email", ""),
                invoice.get("tax_code", ""),
                invoice.get("address", ""),
                format_money(invoice["total_amount"]),
                str(invoice["item_count"]),
            ]
            for col, value in enumerate(values):
                self.invoice_table.setItem(row, col, QTableWidgetItem(value))

        self._sync_invoice_action_state()

    def _selected_invoice_no(self) -> str | None:
        selected = self.invoice_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        invoice_item = self.invoice_table.item(row, 0)
        return invoice_item.text() if invoice_item else None

    def _sync_invoice_action_state(self) -> None:
        has_selected_invoice = self._selected_invoice_no() is not None
        self.view_invoice_detail_btn.setEnabled(has_selected_invoice)
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
            preview_dialog = InvoicePreviewDialog(detail["invoice"], detail["items"], self)
            preview_dialog.exec()
            if not preview_dialog.confirmed:
                return

            export_path = export_invoice_docx(
                detail["invoice"],
                detail["items"],
                self.invoice_export_dir,
            )
            QMessageBox.information(
                self,
                "Thành công",
                f"Đã xuất lại file Word cho hóa đơn {invoice_no}\nFile Word: {export_path}",
            )
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

        highlight_font = QFont(font)
        highlight_font.setPixelSize(px + 2)
        for widget in [getattr(self, "total_goods_text_label", None), getattr(self, "total_goods_label", None)]:
            if widget is not None:
                widget.setFont(highlight_font)

        export_font = QFont(font)
        export_font.setPixelSize(px + 2)
        if getattr(self, "export_btn", None) is not None:
            self.export_btn.setFont(export_font)
