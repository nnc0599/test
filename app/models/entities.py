from dataclasses import dataclass


@dataclass
class Product:
    product_code: str
    name: str
    warranty: str
    unit: str
    quantity: int
    sale_price: int
    updated_at: str
    description: str
    note: str


@dataclass
class Customer:
    customer_code: str
    full_name: str
    phone: str
    address: str
    tax_code: str
    note: str


@dataclass
class InvoiceItem:
    product_code: str
    product_name: str
    quantity: int
    unit_price: int
    line_total: int
