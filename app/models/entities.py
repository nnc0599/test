from dataclasses import dataclass


@dataclass
class Product:
    product_code: str
    name: str
    unit: str
    quantity: int
    sale_price: int
    updated_at: str
    description: str
    note: str


@dataclass
class Customer:
    full_name: str
    phone: str
    address: str
    note: str


@dataclass
class Invoice:
    invoice_no: str
    created_at: str
    customer_name: str
    phone: str
    address: str
    total_amount: int


@dataclass
class InvoiceItem:
    product_code: str
    product_name: str
    quantity: int
    unit_price: int
    line_total: int
