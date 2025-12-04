import os
from datetime import datetime

from benedict import benedict
from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.dataframe import DataFrame
from reggie_concurio import caches
from reggie_core import logs, objects, paths
from reggie_tools import clients, genie

from invoice_ui.models.invoice import (
    GenieStatus,
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


# Global state: current GenieResponse or None
_current_response: genie.GenieResponse | None = None


class InvoiceServiceImpl(InvoiceService):
    _TABLE_NAME = (
        os.getenv("INVOICE_TABLE_NAME", "")
        or "reggie_pierce.invoice_pipeline_dev.info_parse"
    )
    _DISK_CACHE = caches.DiskCache(paths.temp_dir() / "invoice_service_v2")

    def __init__(self) -> None:
        self._spark = clients.spark()
        genie_space_id = os.getenv("INVOICE_GENIE_SPACE_ID", "")
        if genie_space_id:
            wc = clients.workspace_client()
            self._genie_service = genie.Service(wc, genie_space_id)
            self._genie_conversation_id = self._genie_service.create_conversation(
                "Answer questions about invoices"
            ).conversation_id
        else:
            self._genie_service = None
            self._genie_conversation_id = None

    def list_invoices(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> InvoicePage:
        page = max(page, 1)
        page_size = max(page_size, 1)

        df = self._apply_filter(
            self._spark.read.table(self._TABLE_NAME).select(
                "content_hash", "value", "path"
            ),
            query,
        )

        total = df.count()

        window = Window.partitionBy(F.lit(1)).orderBy(
            F.to_date(F.col("value.invoice.invoiceDate"), "M/d/y")
        )

        df = df.withColumn("rn", F.row_number().over(window))

        offset = (page - 1) * page_size
        start = offset + 1
        end = offset + page_size

        df = df.filter((F.col("rn") >= start) & (F.col("rn") <= end))

        rows = df.select("value", "path").collect()

        items = [
            self._parse_invoice(
                benedict(row.value.asDict(recursive=True), keyattr_dynamic=True),
                row.path,
            )
            for row in rows
        ]

        return InvoicePage(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

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

    def _apply_filter(self, df: DataFrame, query: str | None) -> DataFrame:
        if query:
            query = " ".join(query.split())
        if not query:
            return df
        print(f"Query: {query}")
        content_hashes = self._filter_content_hash(query)
        if content_hashes is not None:
            return df.filter(F.col("content_hash").isin(content_hashes))
        df = df.filter(F.lower(F.col("value").cast("string")).contains(query))
        return df

    def _filter_content_hash(self, query: str) -> list[str] | None:
        if not self._genie_service:
            return None

        global _current_response

        cache_key = objects.hash([self._genie_conversation_id, query]).hexdigest()

        def _load():
            global _current_response
            try:
                for response in self._genie_service.chat(
                    self._genie_conversation_id, query
                ):
                    LOG.info(f"Genie response: {objects.to_json(response)}")
                    _current_response = response
                return _current_response
            finally:
                _current_response = None

        genie_response = self._DISK_CACHE.get_or_load(
            cache_key, _load, expire=60 * 5
        ).value

        if not genie_response:
            return None

        for response_query in genie_response.queries:
            try:
                rows = self._spark.sql(response_query).collect()
                return [row.content_hash for row in rows]
            except Exception:
                LOG.warning(f"Query error {response_query}", exc_info=True)
        return None

    @staticmethod
    def get_genie_status() -> GenieStatus:
        """Return the current Genie query status for the UI."""
        global _current_response
        return GenieStatus(_current_response)
