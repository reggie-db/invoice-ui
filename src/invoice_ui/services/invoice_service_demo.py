from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from invoice_ui.data.demo_invoices import DEMO_INVOICES
from invoice_ui.models.invoice import Invoice, InvoicePage
from invoice_ui.services.invoice_service import InvoiceService

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
            items = self._virtual_slice(filtered, start, end)
        else:
            if start >= total:
                return InvoicePage(
                    items=[], total=total, page=page, page_size=page_size
                )
            items = filtered[start:end]

        return InvoicePage(items=items, total=total, page=page, page_size=page_size)

    def _apply_filter(self, query: str | None) -> Sequence[Invoice]:
        if query is None or not query.strip():
            return list(self._invoices)

        normalized = query.strip().lower()
        return [
            invoice
            for invoice in self._invoices
            if any(normalized in value for value in invoice.searchable_terms())
        ]

    def _virtual_slice(
        self,
        base: Sequence[Invoice],
        start: int,
        end: int,
    ) -> Sequence[Invoice]:
        count = max(end - start, 0)
        if count == 0 or not base:
            return []

        result: list[Invoice] = []
        base_len = len(base)
        for offset in range(count):
            index = start + offset
            template = base[index % base_len]
            result.append(self._virtual_invoice(template, index))
        return result

    def _virtual_invoice(self, template: Invoice, index: int) -> Invoice:
        suffix = f"-{index + 1:04d}"
        invoice_details = replace(
            template.invoice,
            invoice_number=f"{template.invoice.invoice_number}{suffix}",
            purchase_order_number=f"{template.invoice.purchase_order_number}{suffix}",
            sales_order_number=f"{template.invoice.sales_order_number}{suffix}",
        )
        ship_to = replace(
            template.ship_to,
            attention=f"{template.ship_to.attention} #{(index % 5) + 1}",
        )
        return replace(template, invoice=invoice_details, ship_to=ship_to)
