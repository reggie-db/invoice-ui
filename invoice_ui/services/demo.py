from __future__ import annotations

from typing import Sequence

from invoice_ui.data.demo_invoices import DEMO_INVOICES
from invoice_ui.models.invoice import Invoice
from invoice_ui.services.base import InvoiceService

"""Demo implementation of the InvoiceService that ships with static data."""


class DemoInvoiceService(InvoiceService):
    """Provides in memory invoice filtering backed by the demo dataset."""

    def __init__(self, invoices: Sequence[Invoice] | None = None) -> None:
        """Initialize the service with the provided invoices or the default set."""
        self._invoices: Sequence[Invoice] = invoices or DEMO_INVOICES

    def search_invoices(self, query: str | None = None) -> Sequence[Invoice]:
        """Return invoices where any searchable field contains the query string."""
        if query is None or not query.strip():
            return self.all_invoices()

        normalized = query.strip().lower()
        return [
            invoice
            for invoice in self._invoices
            if any(normalized in value for value in invoice.searchable_terms())
        ]

    def all_invoices(self) -> Sequence[Invoice]:
        """Return all invoices without filtering."""
        return list(self._invoices)

