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
            raise ValueError("Ma san pham khong duoc de trong")
        if not payload.get("name", "").strip():
            raise ValueError("Ten san pham khong duoc de trong")
        self.repo.add_product(payload)

    def update_product(self, product_code: str, payload: dict) -> None:
        if not payload.get("note", "").strip():
            raise ValueError("Ghi chu bat buoc khi sua thong tin san pham")
        self.repo.update_product(product_code, payload)

    def delete_product(self, product_code: str) -> None:
        self.repo.delete_product(product_code)
