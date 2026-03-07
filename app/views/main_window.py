from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QStringListModel, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
from app.utils.time_utils import now_iso_utc7
from app.views.dialogs.auth_dialog import PasswordDialog
from app.views.dialogs.description_dialog import DescriptionDialog
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

        self.setWindowTitle("Phan mem ban hang")
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.setMinimumSize(900, 600)

        self._apply_base_style()
        self._build_ui()
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
        for idx, title in enumerate(["Len don hang", "San pham", "Bao cao"]):
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
        layout.setSpacing(10)

        customer_box = QGroupBox("Thong tin len don")
        customer_grid = QGridLayout(customer_box)

        self.order_name = QLineEdit()
        self.order_phone = QLineEdit()
        self.order_created_at = QLineEdit()
        self.order_created_at.setReadOnly(True)

        self.order_address = QLineEdit()
        self.order_tax_code = QLineEdit()
        self.order_customer_code = QLineEdit()

        customer_grid.addWidget(QLabel("Nhap ho ten"), 0, 0)
        customer_grid.addWidget(self.order_name, 0, 1)
        customer_grid.addWidget(QLabel("So dien thoai"), 0, 2)
        customer_grid.addWidget(self.order_phone, 0, 3)
        customer_grid.addWidget(QLabel("Ngay tao don"), 0, 4)
        customer_grid.addWidget(self.order_created_at, 0, 5)

        customer_grid.addWidget(QLabel("Dia chi"), 1, 0)
        customer_grid.addWidget(self.order_address, 1, 1, 1, 3)
        customer_grid.addWidget(QLabel("Ma so thue"), 1, 4)
        customer_grid.addWidget(self.order_tax_code, 1, 5)

        customer_grid.addWidget(QLabel("Ma khach hang"), 2, 0)
        customer_grid.addWidget(self.order_customer_code, 2, 1)

        layout.addWidget(customer_box)

        add_item_box = QGroupBox("Them hang hoa")
        add_grid = QGridLayout(add_item_box)

        self.search_product_edit = QLineEdit()
        self.search_product_edit.setPlaceholderText("Tim kiem san pham")
        self.completer_model = QStringListModel([])
        self.product_completer = QCompleter(self.completer_model)
        self.product_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.product_completer.setFilterMode(Qt.MatchContains)
        self.search_product_edit.setCompleter(self.product_completer)

        self.view_desc_btn = QPushButton("Xem them")
        self.view_desc_btn.clicked.connect(self._show_selected_product_desc)

        self.order_qty_spin = QSpinBox()
        self.order_qty_spin.setRange(1, 1_000_000_000)

        self.order_price_spin = QSpinBox()
        self.order_price_spin.setRange(0, 2_000_000_000)

        self.add_line_btn = QPushButton("Them vao danh sach")
        self.add_line_btn.clicked.connect(self._append_invoice_line)

        add_grid.addWidget(QLabel("Tim kiem san pham"), 0, 0)
        add_grid.addWidget(self.search_product_edit, 0, 1, 1, 2)
        add_grid.addWidget(self.view_desc_btn, 0, 3)
        add_grid.addWidget(QLabel("So luong"), 0, 4)
        add_grid.addWidget(self.order_qty_spin, 0, 5)
        add_grid.addWidget(QLabel("Don gia"), 0, 6)
        add_grid.addWidget(self.order_price_spin, 0, 7)
        add_grid.addWidget(self.add_line_btn, 0, 8)

        layout.addWidget(add_item_box)

        self.order_table = QTableWidget(0, 6)
        self.order_table.setHorizontalHeaderLabels(
            ["STT", "Ma hang", "Ten san pham", "So luong", "Don gia", "Thanh tien"]
        )
        self.order_table.verticalHeader().setVisible(False)
        self.order_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.order_table.setSelectionBehavior(QTableWidget.SelectRows)
        header = self.order_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        layout.addWidget(self.order_table)

        payment_box = QGroupBox("Thanh toan")
        payment_form = QFormLayout(payment_box)

        self.ship_fee_spin = QSpinBox()
        self.ship_fee_spin.setRange(0, 2_000_000_000)
        self.ship_fee_spin.valueChanged.connect(self._update_invoice_totals)

        self.total_goods_label = QLabel("0")
        self.total_all_label = QLabel("0")

        payment_form.addRow("Phi ship", self.ship_fee_spin)
        payment_form.addRow("Tong hang", self.total_goods_label)
        payment_form.addRow("Tong cong", self.total_all_label)

        layout.addWidget(payment_box)

        self.export_btn = QPushButton("XUAT HOA DON")
        self.export_btn.setMinimumHeight(58)
        self.export_btn.setStyleSheet(
            "QPushButton { background: #0EA5E9; color: white; font-weight: 800; }"
            "QPushButton:hover { background: #0284C7; }"
            "QPushButton:pressed { background: #0369A1; }"
        )
        self.export_btn.clicked.connect(self._export_invoice)
        layout.addWidget(self.export_btn)

        self.search_product_edit.textChanged.connect(self._refresh_product_completer)
        self.product_completer.activated.connect(self._on_completer_activated)

        return page

    def _build_product_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        actions = QHBoxLayout()
        self.btn_add_product = QPushButton("Them san pham")
        self.btn_edit_product = QPushButton("Sua thong tin")
        self.btn_delete_product = QPushButton("Xoa san pham")

        self.btn_add_product.setStyleSheet(
            "QPushButton { background: #22C55E; color: #0B1A10; }"
            "QPushButton:hover { background: #16A34A; color: white; }"
        )
        self.btn_edit_product.setStyleSheet(
            "QPushButton { background: #FDBA74; color: #4A2A00; }"
            "QPushButton:hover { background: #FB923C; color: white; }"
            "QPushButton:disabled { background: #FED7AA; color: #9A3412; }"
        )
        self.btn_delete_product.setStyleSheet(
            "QPushButton { background: #FCA5A5; color: #4C1D1D; }"
            "QPushButton:hover { background: #F87171; color: white; }"
            "QPushButton:disabled { background: #FECACA; color: #7F1D1D; }"
        )

        for btn in [self.btn_add_product, self.btn_edit_product, self.btn_delete_product]:
            btn.setMinimumHeight(56)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            actions.addWidget(btn)

        layout.addLayout(actions)

        self.product_table = QTableWidget(0, 6)
        self.product_table.setHorizontalHeaderLabels(
            ["Ma san pham", "Ten san pham", "So luong", "Gia ban", "Mo ta", "Ngay cap nhat"]
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
        self.btn_delete_product.setEnabled(False)

        self.btn_add_product.clicked.connect(self._on_add_product)
        self.btn_edit_product.clicked.connect(self._on_edit_product)
        self.btn_delete_product.clicked.connect(self._on_delete_product)
        self.product_table.itemSelectionChanged.connect(self._sync_product_action_state)

        return page

    def _build_report_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        cards = QHBoxLayout()
        self.today_card = self._build_card("Doanh thu hom nay")
        self.month_card = self._build_card("Doanh thu thang")
        cards.addWidget(self.today_card)
        cards.addWidget(self.month_card)
        layout.addLayout(cards)

        panel = QHBoxLayout()

        self.day_table = QTableWidget(0, 2)
        self.day_table.setHorizontalHeaderLabels(["Ngay", "Doanh thu"])
        self.day_table.verticalHeader().setVisible(False)
        self.day_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.day_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.day_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        self.month_table = QTableWidget(0, 2)
        self.month_table.setHorizontalHeaderLabels(["Thang", "Doanh thu"])
        self.month_table.verticalHeader().setVisible(False)
        self.month_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.month_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.month_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        day_group = QGroupBox("Thong ke theo ngay")
        day_layout = QVBoxLayout(day_group)
        day_layout.addWidget(self.day_table)

        month_group = QGroupBox("Thong ke theo thang")
        month_layout = QVBoxLayout(month_group)
        month_layout.addWidget(self.month_table)

        panel.addWidget(day_group)
        panel.addWidget(month_group)
        layout.addLayout(panel)

        refresh_btn = QPushButton("Lam moi bao cao")
        refresh_btn.clicked.connect(self.refresh_report)
        layout.addWidget(refresh_btn)

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

    def _refresh_product_completer(self, keyword: str) -> None:
        products = self.order_controller.search_products(keyword)
        self.product_map = {item["product_code"]: item for item in products}
        labels = [
            f"{item['product_code']} | {item['name']} | {item.get('description', '')[:70]}"
            for item in products
        ]
        self.completer_model.setStringList(labels)

    def _on_completer_activated(self, label: str) -> None:
        product_code = label.split("|")[0].strip()
        self._set_selected_product(product_code)

    def _set_selected_product(self, product_code: str) -> None:
        product = self.product_map.get(product_code)
        if not product:
            return
        self.selected_product_code = product_code
        self.search_product_edit.setText(f"{product['product_code']} | {product['name']}")
        self.order_price_spin.setValue(int(product["sale_price"]))
        stock = int(product["quantity"])
        self.order_qty_spin.setMaximum(max(stock, 1))
        self.order_qty_spin.setToolTip(f"So luong ton: {stock}")

    def _show_selected_product_desc(self) -> None:
        if not self.selected_product_code:
            QMessageBox.information(self, "Thong bao", "Chua chon san pham")
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
        if not self.selected_product_code:
            QMessageBox.warning(self, "Chua chon", "Ban can chon san pham truoc")
            return
        product = self.product_map.get(self.selected_product_code)
        if not product:
            return

        qty = self.order_qty_spin.value()
        unit_price = self.order_price_spin.value()
        stock = int(product["quantity"])
        if qty > stock:
            QMessageBox.warning(self, "Vuot ton kho", "So luong nhap vuot qua ton kho hien tai")
            return

        line = {
            "product_code": product["product_code"],
            "product_name": product["name"],
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

    def _update_invoice_totals(self) -> None:
        total_goods = sum(int(line["line_total"]) for line in self.invoice_lines)
        ship = self.ship_fee_spin.value()
        total_all = total_goods + ship
        self.total_goods_label.setText(format_money(total_goods))
        self.total_all_label.setText(format_money(total_all))

    def _export_invoice(self) -> None:
        try:
            created_at = self.order_created_at.text().strip() or now_iso_utc7()
            invoice_no = f"HD{created_at.replace('-', '').replace(':', '').replace(' ', '')}"
            total_goods = sum(int(line["line_total"]) for line in self.invoice_lines)
            total_all = total_goods + self.ship_fee_spin.value()

            customer_data = {
                "customer_code": self.order_customer_code.text().strip(),
                "full_name": self.order_name.text().strip(),
                "phone": self.order_phone.text().strip(),
                "address": self.order_address.text().strip(),
                "tax_code": self.order_tax_code.text().strip(),
                "note": "Tu dong cap nhat tu len don",
            }
            invoice_data = {
                "invoice_no": invoice_no,
                "created_at": created_at,
                "ship_fee": self.ship_fee_spin.value(),
                "total_amount": total_all,
                "paid_amount": 0,
                "payment_date": created_at,
            }
            self.order_controller.create_invoice(customer_data, invoice_data, self.invoice_lines)

            QMessageBox.information(self, "Thanh cong", f"Da xuat hoa don {invoice_no}")
            self.invoice_lines.clear()
            self._render_invoice_lines()
            self._update_invoice_totals()
            self.refresh_products()
            self.refresh_report()
        except Exception as exc:  # pragma: no cover - dialog feedback
            QMessageBox.critical(self, "Loi", str(exc))

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
                "Xem them",
                product["updated_at"],
            ]
            for col, value in enumerate(base_values):
                if col == 4:
                    btn = QPushButton("Xem them")
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
        self.btn_delete_product.setEnabled(has_selection)

    def _on_add_product(self) -> None:
        if not PasswordDialog.verify(self, "Xac thuc them san pham"):
            return
        dlg = ProductFormDialog(self, mode="add")
        if dlg.exec() != ProductFormDialog.Accepted:
            return
        try:
            self.product_controller.create_product(dlg.payload())
            self.refresh_products()
            QMessageBox.information(self, "Thanh cong", "Da them san pham moi")
        except Exception as exc:
            QMessageBox.critical(self, "Loi", str(exc))

    def _on_edit_product(self) -> None:
        code = self._selected_product_code()
        if not code:
            return
        if not PasswordDialog.verify(self, "Xac thuc sua thong tin"):
            return

        product = self.product_map.get(code)
        if not product:
            QMessageBox.warning(self, "Khong tim thay", "San pham da chon khong ton tai")
            return

        dlg = ProductFormDialog(self, mode="edit", initial=product)
        if dlg.exec() != ProductFormDialog.Accepted:
            return

        try:
            self.product_controller.update_product(code, dlg.payload())
            self.refresh_products()
            QMessageBox.information(self, "Thanh cong", "Da cap nhat san pham")
        except Exception as exc:
            QMessageBox.critical(self, "Loi", str(exc))

    def _on_delete_product(self) -> None:
        code = self._selected_product_code()
        if not code:
            return

        if not PasswordDialog.verify(self, "Xac thuc xoa san pham"):
            return

        ok = QMessageBox.question(
            self,
            "Xac nhan xoa",
            f"Ban co chac chan muon xoa san pham ma {code}?",
        )
        if ok != QMessageBox.Yes:
            return

        if not PasswordDialog.verify(self, "Nhap lai mat khau de xac nhan xoa"):
            return

        try:
            self.product_controller.delete_product(code)
            self.refresh_products()
            QMessageBox.information(self, "Thanh cong", "Da xoa san pham")
        except Exception as exc:
            QMessageBox.critical(self, "Loi", str(exc))

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

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_font_by_window_size()

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
