import os
from datetime import datetime

from benedict import benedict
from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.dataframe import DataFrame
from reggie_concurio import caches
from reggie_core import logs, objects, paths
from reggie_tools import clients, genie

from invoice_ui.models.common import GenieStatusMessage
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

"""Spark-backed implementation of InvoiceService with Genie AI support."""

LOG = logs.logger(__file__)


class InvoiceServiceImpl(InvoiceService):
    """Invoice service implementation using Databricks Spark and Genie AI."""

    _DISK_CACHE = caches.DiskCache(paths.temp_dir() / "invoice_service_v2")

    def __init__(self) -> None:
        self._spark = clients.spark()
        self.table_name = os.getenv("INVOICE_TABLE_NAME")
        assert self.table_name, "INVOICE_TABLE_NAME is not set"
        genie_space_id = os.getenv("INVOICE_GENIE_SPACE_ID", None)
        if genie_space_id:
            wc = clients.workspace_client()
            self._genie_service = genie.Service(wc, genie_space_id)
            self._genie_conversation_id = self._genie_service.create_conversation(
                "Answer questions about invoices"
            ).conversation_id
        else:
            self._genie_service = None
            self._genie_conversation_id = None

    @property
    def ai_available(self) -> bool:
        """Return True if AI-powered search is available."""
        return self._genie_service is not None

    def list_invoices(
        self,
        query: str | None = None,
        page: int = 1,
        page_size: int = 10,
        use_ai: bool = True,
    ) -> InvoicePage:
        """
        List invoices with optional filtering and pagination.

        Args:
            query: Search query string for filtering.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            use_ai: Whether to use AI-powered search (if available).
        """
        page = max(page, 1)
        page_size = max(page_size, 1)

        df = self._apply_filter(
            self._spark.read.table(self.table_name).select(
                "content_hash", "value", "path"
            ),
            query,
            use_ai=use_ai,
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
        """Parse a benedict dictionary into an Invoice dataclass."""
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

    def _apply_filter(
        self, df: DataFrame, query: str | None, use_ai: bool = True
    ) -> DataFrame:
        """Apply search filter to DataFrame, using Genie AI if available and enabled."""
        if query:
            query = " ".join(query.split())
        if not query:
            return df

        LOG.info("Filtering with query: %s (use_ai=%s)", query, use_ai)

        # Only use Genie if AI is enabled
        if use_ai:
            content_hashes = self._filter_content_hash(query)
            if content_hashes is not None:
                return df.filter(F.col("content_hash").isin(content_hashes))

        # Fall back to plain text search
        df = df.filter(F.lower(F.col("value").cast("string")).contains(query.lower()))
        return df

    def _filter_content_hash(self, query: str) -> list[str] | None:
        """Use Genie AI to get content hashes matching the query."""
        if not self._genie_service:
            return None

        cache_key = objects.hash([self._genie_conversation_id, query]).hexdigest()

        def _load() -> list[str] | None:
            try:
                for response in self._genie_service.chat(
                    self._genie_conversation_id, query
                ):
                    LOG.info("Genie response: %s", objects.to_json(response))
                    # Broadcast status update via WebSocket
                    genie_status_message = GenieStatusMessage.from_response(response)
                    if genie_status_message.status or genie_status_message.message:
                        _broadcast_status(genie_status_message)
                    for response_query in response.queries():
                        try:
                            df = self._spark.sql(response_query)
                            if "content_hash" in df.columns:
                                content_hashes = [
                                    row.content_hash for row in df.collect()
                                ]
                                if content_hashes:
                                    return content_hashes
                        except Exception:
                            LOG.warning("Query error %s", response_query, exc_info=True)
                return None
            finally:
                # Send final "inactive" status
                _broadcast_status(GenieStatusMessage(active=False))

        content_hashes = self._DISK_CACHE.get_or_load(
            cache_key, _load, expire=60 * 5
        ).value
        LOG.info("Content hashes: %s", content_hashes)
        return content_hashes


def _broadcast_status(status: GenieStatusMessage) -> None:
    """Broadcast Genie status update via WebSocket."""
    try:
        from invoice_ui.ws_server import broadcast_genie_status

        broadcast_genie_status(status.to_dict())
    except ImportError:
        pass  # WebSocket not initialized
    except Exception as e:
        LOG.warning("Failed to broadcast Genie status: %s", e)
