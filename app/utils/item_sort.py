from __future__ import annotations

import unicodedata

from app.config import PRODUCT_CATEGORY_DISPLAY_PRIORITY


CATEGORY_DISPLAY_PRIORITY = {
    category: index for index, category in enumerate(PRODUCT_CATEGORY_DISPLAY_PRIORITY)
}
DEFAULT_CATEGORY_PRIORITY = len(CATEGORY_DISPLAY_PRIORITY)


def _normalize_text(value: object) -> str:
    text = str(value or "").strip().casefold()
    return "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )


def _infer_category(category: object, *texts: object) -> str:
    normalized_category = str(category or "").strip()
    if normalized_category in CATEGORY_DISPLAY_PRIORITY:
        return normalized_category

    normalized_text = " ".join(_normalize_text(text) for text in texts if str(text or "").strip())

    if not normalized_text:
        return ""
    if "hybrid" in normalized_text:
        return "Biến tần Hybrid"
    if "luu tru 48" in normalized_text:
        return "Pin lưu trữ 48V"
    if "luu tru 24" in normalized_text:
        return "Pin lưu trữ 24V"
    if "bien tan bom" in normalized_text:
        return "Biến tần bơm"
    if any(keyword in normalized_text for keyword in ["tam pin", "pin nang luong", "nlmt", "solar panel"]):
        return "Pin NLMT"
    if any(keyword in normalized_text for keyword in ["khung", "kep", "ray", "jack", "cap", "day dien", "phu kien"]):
        return "Phụ kiện"
    if any(keyword in normalized_text for keyword in ["bien tan", "inverter"]):
        return "Biến tần"
    return ""


def category_display_priority(category: object) -> int:
    normalized_category = str(category or "").strip()
    return CATEGORY_DISPLAY_PRIORITY.get(normalized_category, DEFAULT_CATEGORY_PRIORITY)


def sort_products_by_category_priority(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda item: (
            category_display_priority(
                _infer_category(
                    item.get("category"),
                    item.get("name"),
                    item.get("product_name"),
                    item.get("product_code"),
                )
            ),
            str(item.get("name") or item.get("product_name") or "").casefold(),
            str(item.get("product_code") or "").casefold(),
        ),
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