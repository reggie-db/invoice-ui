"""
Data models and serialization helpers for the Invoice Search UI.

This package provides:
- Invoice domain models (Invoice, LineItem, Party, etc.)
- Application state models (AppState, GenieTableResult)
- Serialization/deserialization for dcc.Store compatibility

All models use Python dataclasses for type safety and IDE support.
"""

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
