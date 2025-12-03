from __future__ import annotations

import json
import os
from datetime import datetime

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
from invoice_ui.utils import parse_date

LOG = logs.logger(__file__)


class InvoiceServiceImpl(InvoiceService):
    _TABLE_NAME = (
        os.getenv("INVOICE_TABLE_NAME", "")
        or "reggie_pierce.invoice_pipeline_dev.info_parse"
    )

    def __init__(self) -> None:
        self._spark = clients.spark()

    def list_invoices(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> InvoicePage:
        page = max(page, 1)
        page_size = max(page_size, 1)

        df = self._spark.read.table(self._TABLE_NAME).select("value", "path")

        if query:
            q = query.strip().lower()
            if q:
                df = df.filter(F.lower(F.col("value").cast("string")).contains(q))

        total = df.count()

        offset = (page - 1) * page_size

        window = Window.orderBy(F.to_date(F.col("value.invoice.invoiceDate"), "M/d/y"))

        df = df.withColumn("rn", F.row_number().over(window))
        df = df.filter((F.col("rn") > offset) & (F.col("rn") <= offset + page_size))

        rows = df.select("value", "path").collect()

        items = []
        for row in rows:
            value = row.value
            if isinstance(value, str):
                value = json.loads(value)
            elif hasattr(value, "asDict"):
                value = value.asDict(recursive=True)
            items.append(
                self._parse_invoice(benedict(value, keyattr_dynamic=True), row.path)
            )

        invoice_page = InvoicePage(
            items=items, total=total, page=page, page_size=page_size
        )
        LOG.info(f"Invoice page: {invoice_page}")
        return invoice_page

    def _parse_invoice(self, b: benedict, path: str) -> Invoice:
        line_items = [
            LineItem(
                description=li.get("description", ""),
                serial_numbers=li.get("serialNumbers") or [],
                line_number=li.get("lineNumber", ""),
                quantity_shipped=li.get("quantityShipped") or 0,
                manufacturer_part_number=li.get("manufacturerPartNumber", ""),
                unit_price=float(li.get("unitPrice") or 0),
                extended_price=float(li.get("extendedPrice") or 0),
                quantity_ordered=li.get("quantityOrdered") or 0,
            )
            for li in b.get("lineItems", [])
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
