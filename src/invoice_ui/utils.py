"""Helper functions for invoice processing and formatting."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from invoice_ui.models.invoice import Invoice

"""Utility functions for invoice data manipulation and formatting."""


def parse_date(date_str: str | None) -> datetime | None:
    """
    Parse a date string in m/d/y format to a datetime object.

    Args:
        date_str: Date string in m/d/y format (e.g., "12/25/2024") or ISO format

    Returns:
        datetime object if parsing succeeds, None otherwise
    """
    if not date_str:
        return None

    # Try m/d/y format first (e.g., "12/25/2024", "1/5/2024")
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y")
    except ValueError:
        pass

    # Try m/d/y with 2-digit year (e.g., "12/25/24")
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%y")
    except ValueError:
        pass

    # Try ISO format as fallback (e.g., "2024-12-25")
    try:
        return datetime.fromisoformat(date_str.strip())
    except (ValueError, TypeError):
        pass

    return None


def format_currency(value: float, currency: str) -> str:
    """Format a currency amount using the currency symbol."""
    return f"{currency} {value:,.2f}"


def matches_query(invoice: "Invoice", query: str) -> bool:
    """Check if an invoice matches the search query."""
    normalized = query.strip().lower()
    if not normalized:
        return True
    return any(normalized in value for value in invoice.searchable_terms())


def virtual_slice(
    base: Sequence["Invoice"],
    start: int,
    end: int,
) -> Sequence["Invoice"]:
    """Generate a virtual slice of invoices for infinite scroll."""
    count = end - start
    base_len = len(base)
    return [
        virtual_invoice(base[(start + offset) % base_len], start + offset)
        for offset in range(count)
    ]


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
