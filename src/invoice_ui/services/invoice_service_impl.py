from __future__ import annotations

from dataclasses import replace
from json import JSONDecodeError, loads
from typing import Sequence

from pyspark.sql import Row
from reggie_core import logs
from reggie_tools import clients

from invoice_ui.models.invoice import (
    Invoice,
    InvoiceDetails,
    InvoicePage,
    LineItem,
    Money,
    Party,
    ShipTo,
    Totals,
)
from invoice_ui.services.invoice_service import InvoiceService

"""Invoice service implementation that hydrates invoices from the Spark info column."""

LOG = logs.logger(__file__)


class InvoiceServiceImpl(InvoiceService):
    """Loads invoices from the reggie warehouse."""

    _VIRTUAL_TOTAL = 10000
    _TABLE_NAME = "reggie_pierce.invoice.info_extract"

    def __init__(self) -> None:
        """Initialize the service and load invoices from the warehouse."""
        LOG.info("Initializing Spark session for invoice import")
        self._spark = clients.spark()
        self._invoices: Sequence[Invoice] = self._fetch_invoices()
        if not self._invoices:
            raise RuntimeError(
                f"No invoices were retrieved from Spark table '{self._TABLE_NAME}'."
            )

    def list_invoices(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> InvoicePage:
        """Return a paginated slice of invoices that match the optional query."""
        filtered = self._apply_filter(query)
        LOG.info(
            "list_invoices - query:%s page: %s page_size:%s",
            query,
            page,
            page_size,
        )
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

    def _fetch_invoices(self) -> Sequence[Invoice]:
        """Collect invoices from the Spark table and convert them to dataclasses."""
        LOG.info("Reading invoices from table '%s'", self._TABLE_NAME)
        rows = self._spark.read.table(self._TABLE_NAME).selectExpr("info").collect()
        LOG.info("Retrieved %d rows from '%s'", len(rows), self._TABLE_NAME)

        invoices: list[Invoice] = []
        for index, row in enumerate(rows):
            payload = row.info
            if isinstance(payload, str):
                try:
                    payload = loads(payload)
                except JSONDecodeError as exc:
                    raise ValueError(
                        f"Row {index} in table '{self._TABLE_NAME}' contains invalid JSON."
                    ) from exc
            if isinstance(payload, Row):
                payload = payload.asDict(recursive=True)
            if not isinstance(payload, dict):
                raise TypeError(
                    f"Row {index} in table '{self._TABLE_NAME}' did not produce a mapping."
                )
            parsed = self._parse_invoice(payload)
            if parsed is None:
                raise ValueError(
                    f"Row {index} in table '{self._TABLE_NAME}' is missing required invoice fields."
                )
            invoices.append(parsed)
        return invoices

    def _parse_invoice(self, payload: dict | None) -> Invoice | None:
        if not payload:
            return None

        buyer_data = payload.get("buyer") or {}
        seller_data = payload.get("seller") or {}
        ship_to_data = payload.get("shipTo") or {}
        invoice_data = payload.get("invoice") or {}
        totals_data = payload.get("totals") or {}
        amount_due = invoice_data.get("amountDue") or {}

        line_items = [
            LineItem(
                description=item.get("description", ""),
                serial_numbers=item.get("serialNumbers") or [],
                line_number=item.get("lineNumber", ""),
                quantity_shipped=item.get("quantityShipped") or 0,
                manufacturer_part_number=item.get("manufacturerPartNumber", ""),
                unit_price=float(item.get("unitPrice") or 0),
                extended_price=float(item.get("extendedPrice") or 0),
                quantity_ordered=item.get("quantityOrdered") or 0,
            )
            for item in payload.get("lineItems") or []
        ]

        return Invoice(
            line_items=line_items,
            ship_to=ShipTo(
                name=ship_to_data.get("name", ""),
                attention=ship_to_data.get("attention", ""),
                address=ship_to_data.get("address") or [],
            ),
            invoice=InvoiceDetails(
                amount_due=Money(
                    currency=amount_due.get("currency", "USD"),
                    value=float(amount_due.get("value") or 0),
                ),
                invoice_number=invoice_data.get("invoiceNumber", ""),
                invoice_date=invoice_data.get("invoiceDate", ""),
                purchase_order_number=invoice_data.get("purchaseOrderNumber", ""),
                due_date=invoice_data.get("dueDate"),
                sales_order_number=invoice_data.get("salesOrderNumber", ""),
                terms=invoice_data.get("terms", ""),
            ),
            buyer=Party(
                name=buyer_data.get("name", ""),
                address=buyer_data.get("address") or [],
            ),
            seller=Party(
                name=seller_data.get("name", ""),
                address=seller_data.get("address") or [],
            ),
            totals=Totals(
                currency=totals_data.get("currency", "USD"),
                shipping=float(totals_data.get("shipping") or 0),
                subtotal=float(totals_data.get("subtotal") or 0),
                tax=float(totals_data.get("tax") or 0),
                total=float(totals_data.get("total") or 0),
            ),
        )

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
