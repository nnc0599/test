# AI Handoff

Cap nhat: 2026-03-24

## Muc tieu du an

Day la ung dung ban hang desktop viet bang Python + PySide6 + SQLite theo mo hinh MVC. Ung dung tap trung vao 3 luong chinh:

- Len don hang va xuat hoa don/bang bao gia
- Quan ly san pham va ton kho
- Bao cao doanh thu va lich su giao dich

Toan bo xu ly ngay gio dung mui gio UTC+7.

## Cach chay nhanh

Tao moi truong va cai goi:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Chay app:

```bash
python run.py
```

Trong workspace hien tai, Python dang duoc dung la:

```bash
/workspaces/test/.venv/bin/python
```

## Trang thai hien tai

- Nhanh ma noi gon: repo dang sach, khong co thay doi git chua commit tinh den 2026-03-24.
- Entry point: `run.py` goi `app.main.run()`.
- Khi khoi dong, app se `init_schema()` va `seed_sample_products()` truoc khi mo `MainWindow`.
- Schema SQLite dang duoc migrate tai cho, khong reset du lieu cu chi de them cot moi.
- San pham hien co 4 muc gia: `sale_price`, `retail_price`, `worker_price`, `dealer_price`.
- Nhom gia khach hang da duoc day vao luong len don va luu trong `customers.customer_price_group`.
- He thong bao gia da ton tai rieng bang `quotations` va `quotation_items`.
- Quy tac ton kho quan trong:
  - Tao bao gia khong tru ton.
  - Sua bao gia khong tru ton.
  - Xuat bao gia thanh hoa don moi tru ton.

## Xac minh gan nhat

Da chay test sau va pass ngay 2026-03-24:

```bash
/workspaces/test/.venv/bin/python -m unittest tests/test_quotation_inventory.py
```

Ket qua: 2 tests pass.

No xac minh dung bat bien nghiep vu quan trong:

- `create_quotation()` khong lam giam ton kho
- `update_quotation()` khong lam giam ton kho
- `export_quotation_to_invoice()` moi giam ton kho va danh dau bao gia da xuat

## Cau truc va diem vao quan trong

- `run.py`: entry point toi gian.
- `app/main.py`: khoi tao schema, seed du lieu mau, tao controller va mo giao dien chinh.
- `app/database/schema.py`: dinh nghia schema, index, FTS cho tim kiem san pham, va logic migrate them cot.
- `app/models/repositories.py`: nghiep vu truy van SQLite, bao gom san pham, khach hang, hoa don, bao gia.
- `app/controllers/order_controller.py`: luong len don, tao/sua/xuat bao gia.
- `app/views/main_window.py`: giao dien chinh va noi tap trung cac thao tac len don/xuat file.
- `app/utils/invoice_docx.py`: xuat DOCX cho hoa don, bao gia va bao cao.
- `tests/test_quotation_inventory.py`: test hoi quy cho luong bao gia va ton kho.

## Ghi chu ha tang va moi truong

- Trong container Ubuntu, PySide6 can mot so goi he thong de import/chay on dinh: `libgl1`, `libegl1`, `libxkbcommon0`, `libxkbcommon-x11-0`, `libxcb-cursor0`, `libxcb-icccm4`, `libxcb-keysyms1`, `libxcb-render-util0`, `libxcb-shape0`, `libxcb-xinerama0`.
- Neu chay trong Codespaces, GUI can di qua Xvfb + noVNC. Dung script `scripts/run_codespaces_gui.sh`.
- Luong preview/xuat xem truoc dang theo huong: DOCX -> LibreOffice headless -> PDF -> QPdfView.
- Font giong Times New Roman trong container hien dang fallback qua Liberation Serif, nen bo cuc se gan Windows nhung khong trung tuyet doi.

## Canh bao ve boi canh

- Co mot repo memory cu nhac toi `app_b`, nhung workspace hien tai khong co thu muc do. Neu AI khac thay ghi chu nay, uu tien cay thu muc thuc te trong repo hien tai.
- File `=6.8.0` dang nam o root repo; chua thay no tham gia truc tiep vao luong app khi doc nhanh.

## Thu tu doc de vao viec nhanh

1. Doc `README.md` de nam tong quan nghiep vu va cach chay.
2. Doc `app/main.py` de thay luong khoi dong.
3. Doc `app/database/schema.py` de hieu schema/migration.
4. Doc `app/models/repositories.py` va `app/controllers/order_controller.py` de hieu nghiep vu.
5. Doc `tests/test_quotation_inventory.py` neu can nam quy tac ton kho cho bao gia.
6. Doc `app/views/main_window.py` neu can sua luong UI.

## Neu tiep quan cong viec

Neu mot AI khac tiep quan, hay xac minh 4 cau hoi nay truoc khi sua code:

1. Dang sua luong hoa don hay bao gia?
2. Thay doi do co anh huong ton kho khong?
3. Thay doi do co can migration schema SQLite tai cho khong?
4. Thay doi do co anh huong den xuat DOCX/PDF hoac chay trong container/Codespaces khong?