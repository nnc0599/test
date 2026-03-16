from __future__ import annotations

from app.config import PRODUCT_CATEGORY_DISPLAY_PRIORITY


CATEGORY_DISPLAY_PRIORITY = {
    category: index for index, category in enumerate(PRODUCT_CATEGORY_DISPLAY_PRIORITY)
}
DEFAULT_CATEGORY_PRIORITY = len(CATEGORY_DISPLAY_PRIORITY)


def category_display_priority(category: object) -> int:
    normalized_category = str(category or "").strip()
    return CATEGORY_DISPLAY_PRIORITY.get(normalized_category, DEFAULT_CATEGORY_PRIORITY)


def sort_products_by_category_priority(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda item: category_display_priority(item.get("category")),
    )


def sort_items_by_unit_price_desc(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda item: (
            category_display_priority(item.get("category")),
            -int(item.get("unit_price", 0) or 0),
            -int(item.get("line_total", 0) or 0),
            str(item.get("product_name", "") or "").casefold(),
            str(item.get("product_code", "") or "").casefold(),
        ),
    )