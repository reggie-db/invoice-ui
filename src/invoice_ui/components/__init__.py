"""
Reusable Dash UI components for the Invoice Search application.

This package provides modular, composable components:
- genie_table: AG Grid display for Genie query results with SQL highlighting
- invoice_card: Rich invoice detail card with line items and totals
- invoice_results: Results list with infinite scroll and empty states
- invoice_search: Search input with optional AI toggle

All components are pure functions that return Dash html/dcc elements,
making them easy to test and compose.
"""

from invoice_ui.components.genie_table import (
    build_genie_query_details,
    build_genie_table,
)
from invoice_ui.components.invoice_card import build_invoice_card
from invoice_ui.components.invoice_results import (
    build_invoice_results,
    build_loading_state,
)

__all__ = [
    "build_genie_query_details",
    "build_genie_table",
    "build_invoice_card",
    "build_invoice_results",
    "build_loading_state",
]
