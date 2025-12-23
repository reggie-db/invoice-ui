"""
Demo implementation of InvoiceService using static in-memory data.

This service is useful for:
- Local development without Databricks access
- Testing UI components with realistic data
- Demonstrating the application without cloud dependencies

The demo service supports infinite scroll by generating virtual invoice
copies with modified identifiers, simulating a large dataset.
"""

import time
from typing import Sequence

from invoice_ui.data.demo_invoices import DEMO_INVOICES
from invoice_ui.models.common import GenieStatusMessage
from invoice_ui.models.invoice import Invoice, InvoicePage
from invoice_ui.services.invoice_service import InvoiceService
from invoice_ui.utils import matches_query, virtual_slice


class DemoInvoiceService(InvoiceService):
    """
    In-memory invoice service backed by static demo data.

    Provides realistic invoice search functionality without requiring
    Databricks connectivity. Supports text-based filtering and simulates
    infinite scroll with virtual invoice generation.

    Attributes:
        _VIRTUAL_TOTAL: Simulated total count for infinite scroll demo.
    """

    _VIRTUAL_TOTAL = 10000

    def __init__(self, invoices: Sequence[Invoice] | None = None) -> None:
        """
        Initialize with invoice data.

        Args:
            invoices: Custom invoice list, or None to use DEMO_INVOICES.
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

        When no query is provided, returns virtual invoices from the demo
        dataset to simulate infinite scroll. With a query, performs text
        matching against searchable invoice fields.

        Args:
            query: Optional text to filter invoices.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            use_ai: Ignored (demo service has no AI support).

        Returns:
            InvoicePage with matching invoices and pagination metadata.
        """
        # Broadcast demo status via WebSocket (only if searching)
        if query and query.strip():
            _broadcast_demo_status(query)

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
        """Filter invoices based on search query."""
        return [inv for inv in self._invoices if matches_query(inv, query or "")]


def _broadcast_demo_status(query: str) -> None:
    """Broadcast demo processing status via WebSocket."""
    try:
        from invoice_ui.ws_server import broadcast_genie_status

        # Show "processing" status briefly
        broadcast_genie_status(
            GenieStatusMessage(
                active=True,
                status="Processing",
                message=f"Searching for: {query}",
            ).to_dict()
        )

        # Small delay to show the status
        time.sleep(0.3)

        # Clear status
        broadcast_genie_status(GenieStatusMessage(active=False).to_dict())

    except ImportError:
        pass  # WebSocket not initialized
    except Exception:
        pass  # Ignore broadcast errors in demo mode
