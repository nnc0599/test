from __future__ import annotations


def sort_items_by_unit_price_desc(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda item: (
            -int(item.get("unit_price", 0) or 0),
            -int(item.get("line_total", 0) or 0),
            str(item.get("product_name", "") or "").casefold(),
            str(item.get("product_code", "") or "").casefold(),
        ),
    )