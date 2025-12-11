"""Dataclasses and helpers for the invoice UI."""

from invoice_ui.models.common import (
    AppState,
    GenieStatusMessage,
    GenieTableResult,
    PaginationState,
)
from invoice_ui.models.invoice import (
    Invoice,
    InvoiceDetails,
    InvoicePage,
    LineItem,
    Money,
    Party,
    ShipTo,
    Totals,
    deserialize_invoice,
    deserialize_page,
    serialize_invoice,
    serialize_page,
)

__all__ = [
    "AppState",
    "GenieStatusMessage",
    "GenieTableResult",
    "Invoice",
    "InvoiceDetails",
    "InvoicePage",
    "LineItem",
    "Money",
    "PaginationState",
    "Party",
    "ShipTo",
    "Totals",
    "deserialize_invoice",
    "deserialize_page",
    "serialize_invoice",
    "serialize_page",
]
