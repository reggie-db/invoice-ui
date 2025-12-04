import time
from typing import Sequence

from invoice_ui.data.demo_invoices import DEMO_INVOICES
from invoice_ui.models.common import GenieStatusMessage
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
        # Broadcast demo status via WebSocket
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
        items = virtual_slice(filtered, start, end) if unlimited else filtered[start:end]
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
