from app.models.repositories import ProductRepository


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

    def update_product(self, product_code: str, payload: dict) -> None:
        if not payload.get("note", "").strip():
            raise ValueError("Ghi chú là bắt buộc khi sửa thông tin sản phẩm")
        self.repo.update_product(product_code, payload)

    def delete_product(self, product_code: str) -> None:
        self.repo.delete_product(product_code)
