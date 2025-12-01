from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from benedict import benedict
from pyspark.sql import Window
from pyspark.sql.functions import col, row_number
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
    _TABLE_NAME = "reggie_pierce.invoice_pipeline_dev.info_parse"

    def __init__(self) -> None:
        """Initialize the service and connect to the warehouse."""
        LOG.info("Initializing Spark session for invoice import")
        self._spark = clients.spark()
        self._total_count: int | None = None

    def list_invoices(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> InvoicePage:
        """Return a paginated slice of invoices that match the optional query."""
        LOG.info(
            "list_invoices - query:%s page: %s page_size:%s",
            query,
            page,
            page_size,
        )

        page = max(page, 1)
        page_size = max(page_size, 1)
        unlimited = query is None or not query.strip()

        # Fetch invoices with pagination from Spark
        invoices = self._fetch_invoices(query=query, page=page, page_size=page_size)

        # Get total count (cached for performance)
        if self._total_count is None:
            self._total_count = self._get_total_count(query)

        total = self._VIRTUAL_TOTAL if unlimited else self._total_count

        # For unlimited queries, apply virtual slicing to generate infinite scroll effect
        # For filtered queries, return invoices as-is from Spark
        if unlimited and invoices:
            start = (page - 1) * page_size
            end = start + len(invoices)
            items = self._virtual_slice(invoices, start, end)
        else:
            items = invoices

        return InvoicePage(items=items, total=total, page=page, page_size=page_size)

    def _fetch_invoices(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Sequence[Invoice]:
        """Collect invoices from the Spark table with pagination and convert them to dataclasses."""
        LOG.info(
            "Reading invoices from table '%s' - page:%s page_size:%s",
            self._TABLE_NAME,
            page,
            page_size,
        )

        # Calculate offset for pagination
        offset = (page - 1) * page_size

        # Build the base query - select both value and path columns
        df = self._spark.read.table(self._TABLE_NAME).select("value", "path")

        # Apply pagination using Spark SQL window function
        window = Window.orderBy(col("value"))
        df_with_row = df.withColumn("row_num", row_number().over(window))
        df_paginated = df_with_row.filter(
            (col("row_num") > offset) & (col("row_num") <= offset + page_size)
        ).select("value", "path")

        rows = df_paginated.collect()
        dicts = [
            {
                "payload": benedict(
                    row.value.asDict(recursive=True), keyattr_dynamic=True
                ),
                "path": row.path if hasattr(row, "path") else "",
            }
            for row in rows
        ]

        LOG.info(
            "Retrieved %d rows from '%s' (page %s)", len(rows), self._TABLE_NAME, page
        )

        invoices: list[Invoice] = []
        for row_data in dicts:
            invoice = self._parse_invoice(row_data["payload"], row_data.get("path", ""))
            if invoice:
                # Apply client-side filtering if query is provided
                if query and not self._matches_query(invoice, query):
                    continue
                invoices.append(invoice)

        return invoices

    def _get_total_count(self, query: str | None = None) -> int:
        """Get the total count of invoices in the Spark table."""
        LOG.info("Getting total count from table '%s'", self._TABLE_NAME)
        df = self._spark.read.table(self._TABLE_NAME)
        count = df.count()
        LOG.info("Total count: %d", count)
        return count

    def _matches_query(self, invoice: Invoice, query: str) -> bool:
        """Check if an invoice matches the search query."""
        if not query or not query.strip():
            return True
        normalized = query.strip().lower()
        return any(normalized in value for value in invoice.searchable_terms())

    def _parse_invoice(
        self, payload: benedict | dict | None, path: str = ""
    ) -> Invoice | None:
        """Parse a benedict dictionary into an Invoice dataclass."""
        if not payload:
            return None

        b = (
            benedict(payload, keyattr_dynamic=True)
            if not isinstance(payload, benedict)
            else payload
        )

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
            for item in b.get("lineItems", [])
        ]

        return Invoice(
            line_items=line_items,
            ship_to=ShipTo(
                name=b.get("shipTo.name", ""),
                attention=b.get("shipTo.attention", ""),
                address=b.get("shipTo.address", []),
            ),
            invoice=InvoiceDetails(
                amount_due=Money(
                    currency=b.get("invoice.amountDue.currency", "USD"),
                    value=float(b.get("invoice.amountDue.value", 0)),
                ),
                invoice_number=b.get("invoice.invoiceNumber", ""),
                invoice_date=b.get("invoice.invoiceDate", ""),
                purchase_order_number=b.get("invoice.purchaseOrderNumber", ""),
                due_date=b.get("invoice.dueDate"),
                sales_order_number=b.get("invoice.salesOrderNumber", ""),
                terms=b.get("invoice.terms", ""),
            ),
            buyer=Party(
                name=b.get("buyer.name", ""),
                address=b.get("buyer.address", []),
            ),
            seller=Party(
                name=b.get("seller.name", ""),
                address=b.get("seller.address", []),
            ),
            totals=Totals(
                currency=b.get("totals.currency", "USD"),
                shipping=float(b.get("totals.shipping", 0)),
                subtotal=float(b.get("totals.subtotal", 0)),
                tax=float(b.get("totals.tax", 0)),
                total=float(b.get("totals.total", 0)),
            ),
            path=path,
        )

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
