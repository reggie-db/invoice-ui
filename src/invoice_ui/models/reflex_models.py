"""
Reflex-compatible models for the Invoice UI.

These models extend rx.Base so they can be used with rx.foreach and
other Reflex reactive components.
"""

import reflex as rx


class MoneyModel(rx.Base):
    """Monetary amount with currency."""

    currency: str = "USD"
    value: float = 0.0


class PartyModel(rx.Base):
    """Entity involved in the invoice."""

    name: str = ""
    address: list[str] = []


class ShipToModel(rx.Base):
    """Shipping destination with attention line."""

    name: str = ""
    address: list[str] = []
    attention: str = ""


class InvoiceDetailsModel(rx.Base):
    """Invoice metadata."""

    amount_due: MoneyModel = MoneyModel()
    invoice_number: str = ""
    invoice_date: str = ""
    purchase_order_number: str = ""
    due_date: str | None = None
    sales_order_number: str = ""
    terms: str = ""


class LineItemModel(rx.Base):
    """Individual line item."""

    description: str = ""
    serial_numbers: list[str] = []
    line_number: str = ""
    quantity_shipped: int = 0
    manufacturer_part_number: str = ""
    unit_price: float = 0.0
    extended_price: float = 0.0
    quantity_ordered: int = 0


class TotalsModel(rx.Base):
    """Invoice totals."""

    tax: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    subtotal: float = 0.0
    shipping: float = 0.0


class InvoiceModel(rx.Base):
    """Complete invoice model for Reflex."""

    line_items: list[LineItemModel] = []
    ship_to: ShipToModel = ShipToModel()
    invoice: InvoiceDetailsModel = InvoiceDetailsModel()
    buyer: PartyModel = PartyModel()
    seller: PartyModel = PartyModel()
    totals: TotalsModel = TotalsModel()
    path: str = ""


def dict_to_invoice_model(data: dict) -> InvoiceModel:
    """
    Convert a serialized invoice dict to an InvoiceModel.

    Args:
        data: Serialized invoice dictionary.

    Returns:
        InvoiceModel instance.
    """
    inv = data.get("invoice", {})
    amount_due = inv.get("amount_due", {})

    return InvoiceModel(
        line_items=[
            LineItemModel(
                description=li.get("description", ""),
                serial_numbers=li.get("serial_numbers", []),
                line_number=li.get("line_number", ""),
                quantity_shipped=li.get("quantity_shipped", 0),
                manufacturer_part_number=li.get("manufacturer_part_number", ""),
                unit_price=li.get("unit_price", 0.0),
                extended_price=li.get("extended_price", 0.0),
                quantity_ordered=li.get("quantity_ordered", 0),
            )
            for li in data.get("line_items", [])
        ],
        ship_to=ShipToModel(
            name=data.get("ship_to", {}).get("name", ""),
            address=data.get("ship_to", {}).get("address", []),
            attention=data.get("ship_to", {}).get("attention", ""),
        ),
        invoice=InvoiceDetailsModel(
            amount_due=MoneyModel(
                currency=amount_due.get("currency", "USD"),
                value=amount_due.get("value", 0.0),
            ),
            invoice_number=inv.get("invoice_number", ""),
            invoice_date=inv.get("invoice_date", ""),
            purchase_order_number=inv.get("purchase_order_number", ""),
            due_date=inv.get("due_date"),
            sales_order_number=inv.get("sales_order_number", ""),
            terms=inv.get("terms", ""),
        ),
        buyer=PartyModel(
            name=data.get("buyer", {}).get("name", ""),
            address=data.get("buyer", {}).get("address", []),
        ),
        seller=PartyModel(
            name=data.get("seller", {}).get("name", ""),
            address=data.get("seller", {}).get("address", []),
        ),
        totals=TotalsModel(
            tax=data.get("totals", {}).get("tax", 0.0),
            total=data.get("totals", {}).get("total", 0.0),
            currency=data.get("totals", {}).get("currency", "USD"),
            subtotal=data.get("totals", {}).get("subtotal", 0.0),
            shipping=data.get("totals", {}).get("shipping", 0.0),
        ),
        path=data.get("path", ""),
    )


