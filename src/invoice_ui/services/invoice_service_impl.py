from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Sequence

from benedict import benedict
from pyspark.sql import Window
from pyspark.sql import functions as F
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
from invoice_ui.utils.invoice_helpers import matches_query, parse_date, virtual_slice

"""Invoice service implementation that loads invoices from Spark table."""

LOG = logs.logger(__file__)


class InvoiceServiceImpl(InvoiceService):
    """Loads invoices from the warehouse."""

    _VIRTUAL_TOTAL = 10000
    _TABLE_NAME = os.getenv("INVOICE_TABLE_NAME", "")
    if not _TABLE_NAME:
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
            items = virtual_slice(invoices, start, end)
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
        if query:
            query = query.lower().strip()
            if query:
                df = df.filter(F.lower(F.col("value").cast("string")).contains(query))

        # Apply pagination using Spark SQL window function
        window = Window.orderBy(F.to_date(F.col("value.invoice.invoiceDate"), "M/d/y"))
        df_with_row = df.withColumn("row_num", F.row_number().over(window))
        df_paginated = df_with_row.filter(
            (F.col("row_num") > offset) & (F.col("row_num") <= offset + page_size)
        ).select("value", "path")

        rows = df_paginated.collect()
        dicts = []
        for row in rows:
            # Handle value column - could be JSON string or Row object
            value_data = row.value
            if isinstance(value_data, str):
                value_data = json.loads(value_data)
            elif hasattr(value_data, "asDict"):
                value_data = value_data.asDict(recursive=True)
            dicts.append(
                {
                    "payload": benedict(value_data, keyattr_dynamic=True),
                    "path": getattr(row, "path", ""),
                }
            )

        LOG.info(
            "Retrieved %d rows from '%s' (page %s)", len(rows), self._TABLE_NAME, page
        )

        invoices: list[Invoice] = []
        for row_data in dicts:
            invoice = self._parse_invoice(row_data["payload"], row_data.get("path", ""))
            if invoice:
                # Apply client-side filtering if query is provided
                if query and not matches_query(invoice, query):
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
                invoice_date=parse_date(b.get("invoice.invoiceDate", ""))
                or datetime.now(),
                purchase_order_number=b.get("invoice.purchaseOrderNumber", ""),
                due_date=parse_date(b.get("invoice.dueDate")),
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
