"""
Abstract base class defining the invoice data access contract.

All invoice service implementations must extend InvoiceService and provide
the list_invoices() method. Optional features like AI search and Genie
table results have default no-op implementations.

Implementations:
- DemoInvoiceService: Static in-memory data for development/testing
- InvoiceServiceImpl: Spark DataFrame queries with Genie AI integration
"""

from abc import ABC, abstractmethod

from invoice_ui.models.common import GenieTableResult
from invoice_ui.models.invoice import InvoicePage


class InvoiceService(ABC):
    """
    Abstract base class for invoice data access.

    Subclasses must implement list_invoices() to provide paginated
    invoice data. Optional AI features are disabled by default.
    """

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
        """
        Check if AI-powered search is available.

        Returns:
            True if Genie AI integration is configured and accessible.
            Default implementation returns False.
        """
        return False

    def get_last_genie_table(self) -> GenieTableResult | None:
        """
        Return the last Genie table result from a query without content_hash.

        When Genie returns data that doesn't include a content_hash column
        (meaning it can't be used to filter invoices), the raw results are
        stored and can be retrieved via this method.

        Returns:
            GenieTableResult with columns/rows data, or None if not available.
        """
        return None

    def clear_genie_table(self) -> None:
        """
        Clear any stored Genie table result.

        Called at the start of each new search to reset state from
        previous queries.
        """
        pass
