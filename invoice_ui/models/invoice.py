from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Sequence

"""Dataclasses and helpers that describe invoice data made available to the UI."""


@dataclass(slots=True)
class Money:
    """Represents a monetary amount with an attached currency code."""

    currency: str
    value: float

    def format(self) -> str:
        """Return the monetary amount as a locale aware currency string."""
        return f"{self.currency} {self.value:,.2f}"


@dataclass(slots=True)
class Party:
    """Represents an entity involved with the invoice."""

    name: str
    address: Sequence[str]


@dataclass(slots=True)
class ShipTo(Party):
    """Adds the attention line that is present for shipping details."""

    attention: str


@dataclass(slots=True)
class InvoiceDetails:
    """Stores the identifying invoice metadata."""

    amount_due: Money
    invoice_number: str
    invoice_date: str
    purchase_order_number: str
    due_date: str | None
    sales_order_number: str
    terms: str

    def formatted_invoice_date(self) -> str:
        """Return the invoice date formatted for display."""
        return _format_date(self.invoice_date)

    def formatted_due_date(self) -> str:
        """Return the due date formatted for display or the N/A label."""
        if not self.due_date:
            return "N/A"
        return _format_date(self.due_date)


@dataclass(slots=True)
class LineItem:
    """Represents an individual line item on the invoice."""

    description: str
    serial_numbers: Sequence[str]
    line_number: str
    quantity_shipped: int
    manufacturer_part_number: str
    unit_price: float
    extended_price: float
    quantity_ordered: int


@dataclass(slots=True)
class Totals:
    """Aggregated monetary data for an invoice."""

    tax: float
    total: float
    currency: str
    subtotal: float
    shipping: float

    def as_money(self, value: float) -> str:
        """Format the provided numeric value as currency."""
        return f"{self.currency} {value:,.2f}"


@dataclass(slots=True)
class Invoice:
    """Primary dataclass for invoices."""

    line_items: Sequence[LineItem]
    ship_to: ShipTo
    invoice: InvoiceDetails
    buyer: Party
    seller: Party
    totals: Totals

    def searchable_terms(self) -> List[str]:
        """Return the terms that should be matched when filtering."""
        terms: List[str] = [
            self.invoice.invoice_number,
            self.invoice.purchase_order_number,
            self.invoice.sales_order_number,
            self.ship_to.name,
            self.ship_to.attention,
            self.buyer.name,
            self.seller.name,
        ]
        for line_item in self.line_items:
            terms.append(line_item.description)
            terms.append(line_item.manufacturer_part_number)
            terms.extend(line_item.serial_numbers)
        return [value.lower() for value in terms if value]


def _format_date(date_str: str) -> str:
    """Format a date string stored in ISO format into a readable presentation."""
    parsed = datetime.fromisoformat(date_str)
    return parsed.strftime("%b %d, %Y")

