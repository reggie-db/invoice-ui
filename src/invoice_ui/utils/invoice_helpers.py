"""Helper functions for invoice processing and formatting."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from invoice_ui.models.invoice import Invoice

"""Utility functions for invoice data manipulation and formatting."""


def format_currency(value: float, currency: str) -> str:
    """Format a currency amount using the currency symbol."""
    return f"{currency} {value:,.2f}"


def matches_query(invoice: "Invoice", query: str) -> bool:
    """Check if an invoice matches the search query."""
    if not query or not query.strip():
        return True
    normalized = query.strip().lower()
    return any(normalized in value for value in invoice.searchable_terms())


def virtual_slice(
    base: Sequence["Invoice"],
    start: int,
    end: int,
) -> Sequence["Invoice"]:
    """Generate a virtual slice of invoices for infinite scroll."""
    count = max(end - start, 0)
    if count == 0 or not base:
        return []

    result: list["Invoice"] = []
    base_len = len(base)
    for offset in range(count):
        index = start + offset
        template = base[index % base_len]
        result.append(virtual_invoice(template, index))
    return result


def virtual_invoice(template: "Invoice", index: int) -> "Invoice":
    """Create a virtual invoice copy with modified identifiers for infinite scroll."""
    suffix = f"-{index + 1:04d}"
    invoice_details = replace(
        template.invoice,
        invoice_number=f"{template.invoice.invoice_number}{suffix}",
        purchase_order_number=f"{template.invoice.purchase_order_number}{suffix}",
        sales_order_number=f"{template.invoice.sales_order_number}{suffix}",
    )
    ship_to = replace(
        template.ship_to,
        attention=f"{template.ship_to.attention} #{(index % 5) + 1}",
    )
    return replace(template, invoice=invoice_details, ship_to=ship_to)

