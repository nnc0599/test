# Phần Mềm Bán Hàng (PySide6 + SQLite)

Ứng dụng bán hàng desktop viết bằng Python + PySide6, theo mô hình MVC, sử dụng SQLite làm cơ sở dữ liệu.

## Tính năng chính

- SQLite schema đầy đủ cho:
	- Sản phẩm
	- Khách hàng
	- Hóa đơn bán hàng + danh sách hàng hóa
	- Thanh toán
- Giao diện Qt 1920x1080, có thể kéo giãn, font toàn bộ là `Times New Roman`, cỡ chữ tự co giãn theo kích thước cửa sổ.
- 3 mục lớn chia đều theo chiều ngang:
	- `Lên đơn hàng`
	- `Sản phẩm`
	- `Báo cáo`
- Có hiệu ứng hover, animation chuyển tab, giao diện sáng, rõ ràng.
- Dialog Thêm/Sửa/Xóa sản phẩm có xác thực mật khẩu (`12345678`).
- Bắt buộc nhập ghi chú khi sửa sản phẩm, nếu để trống thì nút `OK` bị vô hiệu hóa.
- Tab Báo cáo có thống kê doanh thu theo ngày/tháng, danh sách khách hàng đã lưu và danh sách hóa đơn có thể xem chi tiết.
- Múi giờ sử dụng UTC+7.
- Database sản phẩm gồm: mã sản phẩm, tên sản phẩm, đơn vị tính, số lượng, giá bán, ngày cập nhật, mô tả chi tiết, ghi chú.
- Database khách hàng gồm: họ tên, số điện thoại, địa chỉ, ghi chú.
- Database hóa đơn gồm: số hóa đơn, ngày tạo, tên khách hàng, số điện thoại, địa chỉ, tổng số tiền.

## Cấu trúc thư mục

```text
.
|-- app
|   |-- main.py
|   |-- config.py
|   |-- controllers
|   |   |-- order_controller.py
|   |   |-- product_controller.py
|   |   `-- report_controller.py
|   |-- database
|   |   |-- connection.py
|   |   `-- schema.py
|   |-- models
|   |   |-- entities.py
|   |   `-- repositories.py
|   |-- utils
|   |   |-- invoice_docx.py
|   |   `-- time_utils.py
|   `-- views
|       |-- dialogs
|       |   |-- auth_dialog.py
|       |   |-- description_dialog.py
|       |   |-- invoice_detail_dialog.py
|       |   |-- invoice_preview_dialog.py
|       |   |-- product_dialog.py
|       |   `-- product_history_dialog.py
|       `-- main_window.py
|-- data
|   |-- .preview_assets
|   |   |-- image1.png
|   |   `-- image2.png
|   `-- sales_app.db (tự tạo khi chạy)
|-- scripts
|   |-- read_current_database.py
|   `-- run_codespaces_gui.sh
|-- template.docx
|-- requirements.txt
`-- run.py
```

## Cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chạy chương trình

```bash
python run.py
```

## Đọc dữ liệu từ database hiện tại

Repo có sẵn script [scripts/read_current_database.py](scripts/read_current_database.py) để đọc dữ liệu trong database SQLite hiện tại của app và in ra JSON.

1. Đọc toàn bộ bảng:

```bash
/workspaces/test/.venv/bin/python scripts/read_current_database.py
```

2. Chỉ đọc một bảng, ví dụ hóa đơn:

```bash
/workspaces/test/.venv/bin/python scripts/read_current_database.py --table invoices
```

3. Ghi dữ liệu ra file JSON:

```bash
/workspaces/test/.venv/bin/python scripts/read_current_database.py --output data/db_dump.json
```

4. Đọc nhiều bảng cùng lúc:

```bash
/workspaces/test/.venv/bin/python scripts/read_current_database.py --table invoices --table invoice_items --table customers
```

Tại màn hình `Sản phẩm`:

- `Thêm sản phẩm`: mở form thêm mới, ngày cập nhật được gán tự động theo UTC+7.
- `Sửa thông tin`: chỉ bật khi đã chọn sản phẩm; bắt buộc nhập `Ghi chú`, nếu để trống thì nút `OK` bị vô hiệu hóa.
- `Xóa sản phẩm`: cần chọn sản phẩm, xác nhận xóa và nhập lại mật khẩu thêm một lần nữa.

## Chạy GUI trong Codespaces

Nếu mở repo trong GitHub Codespaces, app PySide6 không thể dùng X11 của máy host trực tiếp. Repo này có script để chạy GUI qua trình duyệt bằng Xvfb + noVNC:

```bash
chmod +x scripts/run_codespaces_gui.sh
./scripts/run_codespaces_gui.sh start
```

Script sẽ in ra URL dạng:

```text
https://<codespace-name>-6080.app.github.dev/vnc.html?autoconnect=1&resize=scale
```

Lệnh bổ sung:

```bash
./scripts/run_codespaces_gui.sh status
./scripts/run_codespaces_gui.sh stop
./scripts/run_codespaces_gui.sh restart
```

## Mật khẩu quản trị mặc định

- `12345678`

## Ghi chú kỹ thuật

- Dữ liệu ngày giờ được lấy theo UTC+7 trong toàn bộ app.
- Tổng tiền hóa đơn bằng tổng tiền hàng trong đơn hiện tại.
- Khi xuất hóa đơn, app tự động:
	- Lưu/Cập nhật thông tin khách hàng
	- Lưu hóa đơn + chi tiết hóa đơn
	- Trừ tồn kho
	- Tạo bản ghi thanh toán