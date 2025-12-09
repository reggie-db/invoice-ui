"""
Demo implementation of the InvoiceService that ships with static data.

This service provides in-memory invoice filtering backed by a demo dataset,
useful for development and testing without Databricks connectivity.
"""

import time
from typing import Sequence

from invoice_ui.data.demo_invoices import DEMO_INVOICES
from invoice_ui.models.invoice import Invoice, InvoicePage
from invoice_ui.services.invoice_service import InvoiceService
from invoice_ui.utils import matches_query, virtual_slice


class DemoInvoiceService(InvoiceService):
    """Provides in memory invoice filtering backed by the demo dataset."""

    _VIRTUAL_TOTAL = 10000

    def __init__(self, invoices: Sequence[Invoice] | None = None) -> None:
        """
        Initialize the service with the provided invoices or the default set.

        Args:
            invoices: Optional custom invoice list for testing.
        """
        self._invoices: Sequence[Invoice] = invoices or DEMO_INVOICES

    @property
    def ai_available(self) -> bool:
        """Return True if AI-powered search is available (always False for demo)."""
        return False

    def list_invoices(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 10,
        use_ai: bool = True,
    ) -> InvoicePage:
        """
        Return a paginated slice of invoices that match the optional query.

        Args:
            query: Search query string for filtering.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            use_ai: Ignored in demo mode (no AI available).

        Returns:
            Paginated invoice results.
        """
        # Add small delay to simulate network latency
        if query and query.strip():
            time.sleep(0.3)

        filtered = self._apply_filter(query)
        unlimited = not query or not query.strip()
        page, page_size = max(page, 1), max(page_size, 1)
        start = (page - 1) * page_size

        total = self._VIRTUAL_TOTAL if unlimited else len(filtered)
        if not filtered or start >= total:
            return InvoicePage(items=[], total=total, page=page, page_size=page_size)

        end = min(start + page_size, total)
        items = (
            virtual_slice(filtered, start, end) if unlimited else filtered[start:end]
        )
        return InvoicePage(items=items, total=total, page=page, page_size=page_size)

    def _apply_filter(self, query: str | None) -> Sequence[Invoice]:
        """
        Filter invoices based on search query.

        Args:
            query: Search query string.

        Returns:
            Filtered list of invoices.
        """
        return [inv for inv in self._invoices if matches_query(inv, query or "")]
