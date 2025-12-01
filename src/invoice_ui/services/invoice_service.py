from __future__ import annotations

from abc import ABC, abstractmethod

from invoice_ui.models.invoice import InvoicePage

"""Abstract base classes for invoice data access."""


class InvoiceService(ABC):
    """Defines the contract for retrieving invoices."""

    @abstractmethod
    def list_invoices(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> InvoicePage:
        """Return a paginated set of invoices using the provided filters."""
