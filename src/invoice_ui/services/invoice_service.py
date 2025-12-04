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
        use_ai: bool = True,
    ) -> InvoicePage:
        """
        Return a paginated set of invoices using the provided filters.

        Args:
            query: Search query string for filtering.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            use_ai: Whether to use AI-powered search (if available).
        """

    @property
    def ai_available(self) -> bool:
        """Return True if AI-powered search is available."""
        return False
