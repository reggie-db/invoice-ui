from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from invoice_ui.models.invoice import Invoice

"""Abstract base classes for invoice data access."""


class InvoiceService(ABC):
    """Defines the contract for retrieving invoices."""

    @abstractmethod
    def search_invoices(self, query: str | None = None) -> Sequence[Invoice]:
        """Return invoices that match the provided search query."""

    @abstractmethod
    def all_invoices(self) -> Sequence[Invoice]:
        """Return all invoices without applying filters."""

