# Sales Desktop App (PySide6 + SQLite)

Ung dung ban hang desktop viet bang Python + PySide6, theo mo hinh MVC.

## Tinh nang chinh

- SQLite schema day du cho:
	- San pham
	- Khach hang
	- Hoa don ban hang + danh sach hang hoa
	- Thanh toan
- Giao dien QT 1080x720 (co gian), font `Times New Roman`, chu toi thieu 15px.
- 3 muc lon chia deu theo chieu ngang:
	- `Len don hang`
	- `San pham`
	- `Bao cao`
- Hieu ung hover, animation chuyen tab, giao dien sang toi khi tro chuot.
- Dialog Them/Sua/Xoa san pham co xac thuc mat khau (`12345678`).
- Quy tac bat buoc ghi chu khi sua san pham (khong ghi chu thi khong bam duoc `OK`).
- Tab Bao cao doanh thu theo ngay/thang.
- Mui gio su dung UTC+7.

## Cau truc thu muc

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
|   |   `-- time_utils.py
|   `-- views
|       |-- dialogs
|       |   |-- auth_dialog.py
|       |   |-- description_dialog.py
|       |   `-- product_dialog.py
|       `-- main_window.py
|-- data
|   `-- sales_app.db (tu tao khi chay)
|-- requirements.txt
`-- run.py
```

## Cai dat

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chay chuong trinh

```bash
python run.py
```

## Chay GUI trong Codespaces

Neu mo repo trong GitHub Codespaces, app PySide6 khong the dung X11 cua may host truc tiep. Repo nay co script de chay GUI qua trinh duyet bang Xvfb + noVNC:

```bash
chmod +x scripts/run_codespaces_gui.sh
./scripts/run_codespaces_gui.sh start
```

Script se in ra URL dang:

```text
https://<codespace-name>-6080.app.github.dev/vnc.html?autoconnect=1&resize=scale
```

Lenh bo sung:

```bash
./scripts/run_codespaces_gui.sh status
./scripts/run_codespaces_gui.sh stop
./scripts/run_codespaces_gui.sh restart
```

## Mat khau quan tri mac dinh

- `12345678`

## Ghi chu ky thuat

- Du lieu ngay gio duoc lay theo UTC+7 trong toan bo app.
- Tong tien hoa don = tong tien hang + phi ship.
- Khi xuat hoa don, app tu dong:
	- Luu/Cap nhat thong tin khach hang
	- Luu hoa don + chi tiet hoa don
	- Tru ton kho
	- Tao ban ghi thanh toan