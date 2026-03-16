from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl import load_workbook

from app.models.repositories import ProductRepository


PRODUCT_IMPORT_HEADERS = [
    "Mã sản phẩm",
    "Tên sản phẩm",
    "Đơn vị tính",
    "Số lượng",
    "Giá bán",
    "Mô tả",
]

PRODUCT_EXPORT_HEADERS = [
    "Mã sản phẩm",
    "Tên sản phẩm",
    "Đơn vị tính",
    "Số lượng",
    "Giá bán",
    "Mô tả",
    "Ghi chú",
    "Ngày cập nhật",
]


class ProductController:
    def __init__(self, repo: ProductRepository):
        self.repo = repo

    def list_products(self) -> list[dict]:
        return self.repo.list_products()

    def search_products(self, keyword: str) -> list[dict]:
        if not keyword.strip():
            return self.repo.list_products()[:20]
        return self.repo.search_products(keyword)

    def create_product(self, payload: dict) -> None:
        if not payload.get("product_code", "").strip():
            raise ValueError("Mã sản phẩm không được để trống")
        if not payload.get("name", "").strip():
            raise ValueError("Tên sản phẩm không được để trống")
        if self.repo.get_product(payload["product_code"].strip()):
            raise ValueError("Mã sản phẩm đã tồn tại, vui lòng nhập mã khác")
        self.repo.add_product(payload)

    def parse_product_import_file(self, file_path: str) -> tuple[list[dict], int]:
        workbook = load_workbook(filename=Path(file_path), read_only=True, data_only=True)
        try:
            sheet = workbook.active

            header_row = [sheet[f"{column}1"].value for column in ["A", "B", "C", "D", "E", "F"]]
            normalized_headers = [str(value).strip() if value is not None else "" for value in header_row]
            if normalized_headers != PRODUCT_IMPORT_HEADERS:
                raise ValueError("File không đúng biểu mẫu")

            products: list[dict] = []
            missing_code_count = 0
            for row in sheet.iter_rows(min_row=2, max_col=6, values_only=True):
                if row is None:
                    continue
                values = list(row) + [None] * (6 - len(row))
                if all(value is None or str(value).strip() == "" for value in values):
                    continue

                product_code = self._as_text(values[0])
                if not product_code:
                    missing_code_count += 1
                    continue

                products.append(
                    {
                        "product_code": product_code,
                        "name": self._as_text(values[1]),
                        "unit": self._as_text(values[2]),
                        "quantity": self._as_int(values[3]),
                        "sale_price": self._as_int(values[4]),
                        "description": self._as_text(values[5]),
                        "note": "",
                    }
                )

            return products, missing_code_count
        finally:
            workbook.close()

    def create_products(self, payloads: list[dict]) -> None:
        if not payloads:
            return
        self.repo.add_products(payloads)

    def export_product_import_template(self, file_path: str) -> None:
        workbook = Workbook()
        try:
            sheet = workbook.active
            sheet.title = "SanPham"
            sheet.append(PRODUCT_IMPORT_HEADERS)
            sheet.append([
                "SP001",
                "Tên sản phẩm mẫu",
                "cái",
                0,
                0,
                "Mô tả sản phẩm mẫu",
            ])
            workbook.save(file_path)
        finally:
            workbook.close()

    def export_products_to_excel(self, file_path: str) -> None:
        workbook = Workbook()
        try:
            sheet = workbook.active
            sheet.title = "SanPham"
            sheet.append(PRODUCT_EXPORT_HEADERS)

            for product in self.repo.list_products():
                sheet.append(
                    [
                        self._as_text(product.get("product_code")),
                        self._as_text(product.get("name")),
                        self._as_text(product.get("unit")),
                        self._as_int(product.get("quantity")),
                        self._as_int(product.get("sale_price")),
                        self._as_text(product.get("description")),
                        self._as_text(product.get("note")),
                        self._as_text(product.get("updated_at")),
                    ]
                )

            workbook.save(file_path)
        finally:
            workbook.close()

    @staticmethod
    def _as_text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value)).strip()
        return str(value).strip()

    @staticmethod
    def _as_int(value: object) -> int:
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)

        text = str(value).strip()
        if not text:
            return 0

        try:
            return int(text)
        except ValueError:
            return int(float(text))

    def update_product(self, product_code: str, payload: dict) -> None:
        if not payload.get("note", "").strip():
            raise ValueError("Ghi chú là bắt buộc khi sửa thông tin sản phẩm")
        self.repo.update_product(product_code, payload)

    def list_product_update_history(self, product_code: str) -> list[dict]:
        return self.repo.list_product_update_history(product_code)

    def delete_product(self, product_code: str) -> None:
        self.repo.delete_product(product_code)
