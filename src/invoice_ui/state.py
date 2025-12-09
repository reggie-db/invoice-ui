"""
Reflex state management for the Invoice UI application.

This module contains the main application state class that handles
invoice listing, filtering, pagination, and Genie AI search status.
"""

import os
from typing import Generator

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
    total: int = 0
    page_size: int = PAGE_SIZE
    has_more: bool = True

    # Search state
    query: str = ""
    ai_enabled: bool = True
    ai_available: bool = False
    is_loading: bool = True

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

        Yields intermediate states to show loading, then fetches first page.
        """
        self.is_loading = True
        self.invoices = []
        self.has_more = True
        self.ai_available = _get_service().ai_available

        self.load_more()

    def search(self, query: str) -> Generator:
        """
        Event handler for search query changes.

        Uses yield to provide intermediate loading states and Genie status updates.

        Args:
            query: The search query string.
        """
        self.query = query.strip() if query else ""
        self.is_loading = True
        self.invoices = []
        self.page = 1
        yield

        try:
            # Show genie status if AI is enabled and query is provided
            if self.ai_enabled and self.query and self.ai_available:
                self._update_genie_status(
                    True, "Processing", f"Searching: {self.query}"
                )
                yield

            invoice_page = self._fetch_invoices(self.query, 1, self.ai_enabled)
            self.invoices = self._to_models(invoice_page)
            self.total = invoice_page.total
            self.page = invoice_page.page
            self.has_more = invoice_page.has_more
        except Exception as e:
            LOG.error("Search failed: %s", e, exc_info=True)
            self.invoices = []
            self.total = 0
            self.has_more = False
        finally:
            self._update_genie_status(False)
            self.is_loading = False

    @rx.event
    def load_more(self):
        """
        Event handler for infinite scroll pagination.

        Yields intermediate states while loading additional invoices.
        """
        LOG.info(
            "Load Started - has_more: %s length:%s", self.has_more, len(self.invoices)
        )
        if not self.has_more:
            return

        self.is_loading = True
        try:
            next_page = len(self.invoices) // self.page_size + 1
            invoice_page = self._fetch_invoices(self.query, next_page, self.ai_enabled)

            # Append new invoices to existing list
            new_invoices = self._to_models(invoice_page)
            self.invoices = self.invoices + new_invoices
            self.total = invoice_page.total
            self.has_more = len(new_invoices) >= self.page_size
        except Exception as e:
            LOG.error("Failed to load more: %s", e, exc_info=True)
        finally:
            self.is_loading = False
        LOG.info(
            "Load Complete - has_more: %s length:%s", self.has_more, len(self.invoices)
        )

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

    def _fetch_invoices(
        self, query: str | None, page: int, use_ai: bool
    ) -> InvoicePage:
        """Fetch invoices from the service."""
        return _get_service().list_invoices(
            query=query or None,
            page=page,
            page_size=self.page_size,
            use_ai=use_ai,
        )

    def _to_models(self, invoice_page: InvoicePage) -> list[InvoiceModel]:
        """Convert InvoicePage items to InvoiceModel list."""
        return [
            dict_to_invoice_model(serialize_invoice(inv)) for inv in invoice_page.items
        ]
