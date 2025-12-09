"""
Reflex state management for the Invoice UI application.

This module contains the main application state class that handles
invoice listing, filtering, pagination, and Genie AI search status.
"""

import os

import reflex as rx
from reggie_core import logs

from invoice_ui.models.invoice import (
    InvoicePage,
    serialize_invoice,
)
from invoice_ui.models.reflex_models import InvoiceModel, dict_to_invoice_model
from invoice_ui.services import get_invoice_service

LOG = logs.logger(__file__)

# Configuration from environment
PAGE_SIZE = 2
USE_LIVE = os.getenv("INVOICE_UI_USE_LIVE", "true").lower() in {"1", "true", "yes"}
USE_GENERIC_BRANDING = os.getenv("INVOICE_UI_GENERIC", "false").lower() in {
    "1",
    "true",
    "yes",
}

# Branding configuration
APP_TITLE = "Invoice Search" if USE_GENERIC_BRANDING else "Hardware Invoice Search"
APP_SUBTITLE = (
    "Search and browse invoices."
    if USE_GENERIC_BRANDING
    else "Search through computer hardware orders and invoices."
)


def _get_service():
    """Get the configured invoice service (lazy loaded)."""
    return get_invoice_service("impl" if USE_LIVE else "demo")


class InvoiceState(rx.State):
    """
    Main application state for the Invoice UI.

    Handles invoice listing, search, pagination, and Genie AI status.
    """

    # Invoice data using Reflex-compatible models
    invoices: list[InvoiceModel] = []
    total: int = -1
    page_size: int = PAGE_SIZE
    has_more: bool = True
    is_loading: bool = True

    # Search state
    query: str = ""
    ai_enabled: bool = True
    ai_available: bool = False

    # Genie status
    genie_active: bool = False
    genie_status: str = ""
    genie_message: str = ""

    @rx.var
    def result_summary(self) -> str:
        """Generate summary text for search results."""
        noun = "invoice" if self.total == 1 else "invoices"
        base = f"{self.total} {noun} found"
        if self.query and self.query.strip():
            return f'{base} for "{self.query.strip()}"'
        return base

    @rx.var
    def is_empty(self) -> bool:
        """Check if empty state should be shown."""
        return not self.is_loading and len(self.invoices) == 0

    @rx.event
    def on_load(self):
        """
        Event handler for initial page load.
        """
        self.ai_available = _get_service().ai_available
        self._reset()
        self.load_more()

    def set_query(self, query: str):
        """Set the query and reset the state."""
        query = query.strip() if query else ""
        if self.query == query:
            return
        self.query = query
        self._reset()
        self.load_more()

    @rx.event
    def load_more(self):
        """
        Event handler for infinite scroll pagination.
        """
        LOG.info(
            "Load Started - has_more:%s length:%s query:%s ai_enabled:%s ai_available:%s",
            self.has_more,
            len(self.invoices),
            self.query,
            self.ai_enabled,
            self.ai_available,
        )
        if not self.has_more:
            return
        self.is_loading = True
        if self.query and self.ai_enabled and self.ai_available:
            LOG.info("Updating Genie status: %s", f"Searching: {self.query}")
            self._update_genie_status(True, "Processing", f"Searching: {self.query}")

        try:
            LOG.info("Fetching invoices")
            invoice_page = self._fetch_invoices()

            # Append new invoices to existing list
            new_invoices = self._to_models(invoice_page)
            self.invoices = self.invoices + new_invoices
            self.total = invoice_page.total
            self.has_more = len(new_invoices) >= self.page_size
        except Exception as e:
            LOG.error("Failed to load more: %s", e, exc_info=True)
        finally:
            self.is_loading = False

    def toggle_ai(self):
        """Toggle AI search on/off and trigger a new search."""
        self.ai_enabled = not self.ai_enabled
        # Trigger a new search with the current query
        return self.search(self.query)

    def set_ai_enabled(self, enabled: bool):
        """Set AI enabled state."""
        self.ai_enabled = enabled

    def _update_genie_status(self, active: bool, status: str = "", message: str = ""):
        """Update the Genie status indicators."""
        self.genie_active = active
        self.genie_status = status
        self.genie_message = message

    def _reset(self):
        """Reset the state to initial values."""
        self.invoices = []
        self.total = -1
        self.has_more = True
        self.is_loading = True

    def _fetch_invoices(self) -> InvoicePage:
        """Fetch invoices from the service."""
        next_page = len(self.invoices) // self.page_size + 1
        return _get_service().list_invoices(
            query=self.query or None,
            page=next_page,
            page_size=self.page_size,
            use_ai=self.ai_enabled,
        )

    def _to_models(self, invoice_page: InvoicePage) -> list[InvoiceModel]:
        """Convert InvoicePage items to InvoiceModel list."""
        return [
            dict_to_invoice_model(serialize_invoice(inv)) for inv in invoice_page.items
        ]
