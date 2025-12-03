from __future__ import annotations

from typing import Sequence

from invoice_ui.data.demo_invoices import DEMO_INVOICES
from invoice_ui.models.invoice import Invoice, InvoicePage
from invoice_ui.services.invoice_service import InvoiceService
from invoice_ui.utils import matches_query, virtual_slice

"""Demo implementation of the InvoiceService that ships with static data."""


class DemoInvoiceService(InvoiceService):
    """Provides in memory invoice filtering backed by the demo dataset."""

    _VIRTUAL_TOTAL = 10000

    def __init__(self, invoices: Sequence[Invoice] | None = None) -> None:
        """Initialize the service with the provided invoices or the default set."""
        self._invoices: Sequence[Invoice] = invoices or DEMO_INVOICES

    def list_invoices(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> InvoicePage:
        """Return a paginated slice of invoices that match the optional query."""
        filtered = self._apply_filter(query)
        unlimited = query is None or not query.strip()
        if not filtered:
            return InvoicePage(items=[], total=0, page=page, page_size=page_size)

        total = len(filtered)
        page = max(page, 1)
        page_size = max(page_size, 1)
        start = (page - 1) * page_size
        end = start + page_size

        if unlimited:
            total = self._VIRTUAL_TOTAL
            if start >= total:
                return InvoicePage(
                    items=[], total=total, page=page, page_size=page_size
                )
            end = min(end, total)
            items = virtual_slice(filtered, start, end)
        else:
            if start >= total:
                return InvoicePage(
                    items=[], total=total, page=page, page_size=page_size
                )
            items = filtered[start:end]

        return InvoicePage(items=items, total=total, page=page, page_size=page_size)

    def _apply_filter(self, query: str | None) -> Sequence[Invoice]:
        """Filter invoices based on search query."""
        if query is None or not query.strip():
            return list(self._invoices)
        return [invoice for invoice in self._invoices if matches_query(invoice, query)]
