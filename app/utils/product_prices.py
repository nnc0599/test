from __future__ import annotations

from typing import Any


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


def format_money(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def normalize_product_prices(product: dict[str, Any] | None) -> dict[str, int]:
    payload = product or {}
    legacy_price = _as_int(payload.get("sale_price", 0))
    legacy_custom_price = _as_int(payload.get("custom_price", 0))
    retail_source = payload.get("retail_price")
    if retail_source is None or str(retail_source).strip() == "":
        retail_price = legacy_custom_price or legacy_price
    else:
        retail_price = _as_int(retail_source)

    worker_price = _as_int(payload.get("worker_price", 0))
    dealer_price = _as_int(payload.get("dealer_price", 0))
    sale_price = retail_price or worker_price or dealer_price or legacy_custom_price or legacy_price

    return {
        "sale_price": sale_price,
        "retail_price": retail_price,
        "worker_price": worker_price,
        "dealer_price": dealer_price,
    }


def apply_normalized_product_prices(product: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(product or {})
    payload.update(normalize_product_prices(payload))
    return payload


def get_default_order_price(product: dict[str, Any] | None) -> int:
    prices = normalize_product_prices(product)
    for field_name in ("retail_price", "worker_price", "dealer_price", "sale_price"):
        value = prices[field_name]
        if value > 0:
            return value
    return 0


def get_stock_value_price(product: dict[str, Any] | None) -> int:
    prices = normalize_product_prices(product)
    return prices["retail_price"] or prices["worker_price"] or prices["dealer_price"] or prices["sale_price"]


def get_product_price_options(product: dict[str, Any] | None) -> list[tuple[str, str, int]]:
    prices = normalize_product_prices(product)
    retail_price = prices["retail_price"]
    worker_price = prices["worker_price"]
    dealer_price = prices["dealer_price"]

    options: list[tuple[str, str, int]] = []
    if retail_price > 0:
        options.append(("retail_price", "Giá lẻ", retail_price))
    if worker_price > 0:
        options.append(("worker_price", "Giá thợ", worker_price))
    if dealer_price > 0:
        options.append(("dealer_price", "Giá đại lý", dealer_price))

    if options:
        return options

    fallback_price = prices["sale_price"]
    return [("sale_price", "Giá lẻ", fallback_price)]


def build_product_price_lines(product: dict[str, Any] | None) -> list[str]:
    prices = normalize_product_prices(product)
    retail_price = prices["retail_price"]
    worker_price = prices["worker_price"]
    dealer_price = prices["dealer_price"]

    if retail_price > 0 and worker_price <= 0 and dealer_price <= 0:
        return [f"Giá: {format_money(retail_price)}"]

    lines: list[str] = []
    if retail_price > 0:
        lines.append(f"Lẻ: {format_money(retail_price)}")
    if worker_price > 0:
        lines.append(f"Thợ: {format_money(worker_price)}")
    if dealer_price > 0:
        lines.append(f"Đại lý: {format_money(dealer_price)}")

    if not lines:
        lines.append("Giá: 0")
    return lines


def format_product_price_summary(product: dict[str, Any] | None, separator: str = "\n") -> str:
    return separator.join(build_product_price_lines(product))