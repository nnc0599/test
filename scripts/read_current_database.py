from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import DB_PATH
from app.database.connection import get_connection


TABLE_QUERIES = {
    "products": "SELECT * FROM products ORDER BY updated_at DESC, product_code ASC",
    "customers": "SELECT * FROM customers ORDER BY id DESC",
    "invoices": "SELECT * FROM invoices ORDER BY created_at DESC, invoice_no DESC",
    "invoice_items": "SELECT * FROM invoice_items ORDER BY id DESC",
    "payments": "SELECT * FROM payments ORDER BY id DESC",
    "product_update_history": "SELECT * FROM product_update_history ORDER BY changed_at DESC, id DESC",
}


def read_table(table_name: str) -> list[dict]:
    query = TABLE_QUERIES[table_name]
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(row) for row in rows]


def build_payload(selected_tables: list[str]) -> dict:
    return {
        "database_path": str(DB_PATH),
        "tables": {table_name: read_table(table_name) for table_name in selected_tables},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Đọc dữ liệu từ database hiện tại của app và in ra JSON."
    )
    parser.add_argument(
        "--table",
        dest="tables",
        action="append",
        choices=sorted(TABLE_QUERIES.keys()),
        help="Chỉ đọc bảng được chỉ định. Có thể truyền nhiều lần.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Nếu có, ghi JSON ra file thay vì chỉ in ra màn hình.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_tables = args.tables or list(TABLE_QUERIES.keys())
    payload = build_payload(selected_tables)
    content = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"Đã ghi dữ liệu database ra: {args.output}")
        return

    print(content)


if __name__ == "__main__":
    main()