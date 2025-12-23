"""
Spark-backed implementation of InvoiceService with Databricks Genie AI support.

This module provides the production invoice service that:
- Reads invoice data from Unity Catalog tables via Spark
- Integrates with Databricks Genie for natural language queries
- Broadcasts real-time status updates via WebSocket
- Caches Genie query results to disk for performance

The service expects invoice data stored as nested JSON in a `value` column,
with `content_hash` as the unique identifier and `path` pointing to the
source PDF file in DBFS or Volumes.

Genie Integration:
- Queries are sent to a configured Genie space
- If Genie returns content_hash values, they filter the invoice DataFrame
- If Genie returns other data, it's displayed in an AG Grid table
- Query results are cached for 5 minutes to avoid redundant API calls
"""

import functools
import os
from datetime import datetime

from benedict import benedict
from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.dataframe import DataFrame
from reggie_concurio import caches
from reggie_core import logs, objects, paths
from reggie_tools import clients, genie

from invoice_ui.models.common import GenieStatusMessage, GenieTableResult
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


def _parse_invoice(b: benedict, path: str) -> Invoice:
    """
    Parse a benedict dictionary into an Invoice dataclass.

    Uses benedict for safe nested key access (dot notation) to handle
    missing or null values gracefully without raising KeyError.

    Args:
        b: Benedict dict wrapping the invoice JSON structure.
        path: DBFS/Volumes path to the source PDF file.

    Returns:
        Fully populated Invoice dataclass.
    """
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
            invoice_date=parse_date(b.get("invoice.invoiceDate", "")) or datetime.now(),
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


class InvoiceServiceImpl(InvoiceService):
    """
    Production invoice service using Databricks Spark and Genie AI.

    Reads invoice data from a Unity Catalog table and optionally uses
    Databricks Genie for semantic search capabilities. Results are cached
    to disk to minimize redundant Genie API calls.

    Required Environment Variables:
        INVOICE_TABLE_NAME: Fully qualified table name (catalog.schema.table)

    Optional Environment Variables:
        INVOICE_GENIE_SPACE_ID: Genie space ID for AI search

    Attributes:
        table_name: Unity Catalog table containing invoice data.
    """

    # Disk cache for Genie query results (5 minute TTL)
    _DISK_CACHE = caches.DiskCache(paths.temp_dir() / "invoice_service_v2")

    def __init__(self) -> None:
        """
        Initialize the service with table configuration.

        Raises:
            AssertionError: If INVOICE_TABLE_NAME is not set.
        """
        self.table_name = os.getenv("INVOICE_TABLE_NAME")
        assert self.table_name, "INVOICE_TABLE_NAME is not set"
        # Stores the last Genie table result when no content_hash was found
        self._last_genie_table: GenieTableResult | None = None

    def get_last_genie_table(self) -> GenieTableResult | None:
        """
        Return the last Genie table result from a query that had no content_hash.

        This is populated after list_invoices is called with an AI query
        that returns data but no content_hash column.
        """
        return self._last_genie_table

    def clear_genie_table(self) -> None:
        """Clear the stored Genie table result."""
        self._last_genie_table = None

    @property
    def ai_available(self) -> bool:
        """Return True if AI-powered search is available."""
        return self._genie_space_id() is not None

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
            clients.spark()
            .read.table(self.table_name)
            .select("content_hash", "value", "path"),
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
            _parse_invoice(
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

    def _apply_filter(
        self, df: DataFrame, query: str | None, use_ai: bool = True
    ) -> DataFrame:
        """
        Apply search filter to DataFrame, using Genie AI if available and enabled.

        Filter Strategy:
        1. If no query, return unfiltered DataFrame
        2. If AI enabled and Genie returns content_hashes, filter by those
        3. Otherwise, fall back to case-insensitive text search on JSON

        Args:
            df: Source DataFrame with content_hash, value, and path columns.
            query: Search query string (whitespace normalized).
            use_ai: If True and available, use Genie for semantic search.

        Returns:
            Filtered DataFrame matching the search criteria.
        """
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
        """
        Use Genie AI to get content hashes matching the query.

        Sends the query to Databricks Genie and processes the response:
        1. If Genie returns content_hash column, extract values for filtering
        2. If Genie returns other data, store in _last_genie_table for display
        3. Always store the SQL query for UI display

        Results are cached to disk with a 5-minute TTL keyed by conversation
        ID and query text.

        Args:
            query: Natural language query for Genie.

        Returns:
            List of content_hash strings for filtering, or None if Genie
            unavailable or returned non-filterable data.
        """
        if not self.ai_available:
            return None

        # Clear any previous genie table result
        self._last_genie_table = None

        cache_key = objects.hash([self._genie_context()[1], query]).hexdigest()

        def _load() -> dict:
            """Load and return both content_hashes and query info."""
            result = {"content_hashes": None, "genie_table": None}
            try:
                genie_service, conversation_id = self._genie_context()
                genie_description = ""

                for response in genie_service.chat(conversation_id, query):
                    LOG.info("Genie response: %s", objects.to_json(response))
                    # Broadcast status update via WebSocket
                    genie_status_message = GenieStatusMessage.from_response(response)
                    if genie_status_message.status or genie_status_message.message:
                        _broadcast_status(genie_status_message)

                    # Capture any description from Genie
                    if genie_status_message.message:
                        genie_description = genie_status_message.message

                    for response_query in response.queries():
                        try:
                            df = clients.spark().sql(response_query)
                            columns = df.columns

                            if "content_hash" in columns:
                                # Found content_hash column, use for filtering
                                content_hashes = [
                                    row.content_hash for row in df.collect()
                                ]
                                if content_hashes:
                                    result["content_hashes"] = content_hashes
                                    # Store the query info even when content_hash found
                                    result["genie_table"] = {
                                        "columns": columns,
                                        "rows": [],  # No raw data needed
                                        "query": response_query,
                                        "description": genie_description,
                                        "has_content_hash": True,
                                    }
                                    LOG.info(
                                        "Found %d content hashes, query: %s",
                                        len(content_hashes),
                                        response_query[:100],
                                    )
                                    return result
                            else:
                                # No content_hash, capture as raw table data
                                rows = df.limit(100).collect()
                                if rows:
                                    table_rows = [
                                        row.asDict() for row in rows
                                    ]
                                    result["genie_table"] = {
                                        "columns": columns,
                                        "rows": table_rows,
                                        "query": response_query,
                                        "description": genie_description,
                                        "has_content_hash": False,
                                    }
                                    LOG.info(
                                        "Captured Genie table with %d rows, columns: %s",
                                        len(table_rows),
                                        columns,
                                    )
                        except Exception:
                            LOG.warning("Query error %s", response_query, exc_info=True)
                return result
            finally:
                # Send final "inactive" status
                _broadcast_status(GenieStatusMessage(active=False))

        cached_result = self._DISK_CACHE.get_or_load(
            cache_key, _load, expire=60 * 5
        ).value

        # Handle both old format (list) and new format (dict)
        if isinstance(cached_result, list):
            # Old cache format, just content hashes
            content_hashes = cached_result
            LOG.info("Content hashes (old format): %s", content_hashes)
            return content_hashes

        # New format with both content_hashes and genie_table
        content_hashes = cached_result.get("content_hashes") if cached_result else None
        genie_table_data = cached_result.get("genie_table") if cached_result else None

        if genie_table_data:
            self._last_genie_table = GenieTableResult(
                columns=genie_table_data.get("columns", []),
                rows=genie_table_data.get("rows", []),
                query=genie_table_data.get("query", ""),
                description=genie_table_data.get("description", ""),
                has_content_hash=genie_table_data.get("has_content_hash", False),
            )
            LOG.info(
                "Stored Genie result: %d rows, has_content_hash=%s, query=%s",
                len(self._last_genie_table.rows),
                self._last_genie_table.has_content_hash,
                self._last_genie_table.query[:100] if self._last_genie_table.query else "",
            )

        LOG.info("Content hashes: %s", content_hashes)
        return content_hashes

    def _genie_space_id(self) -> str | None:
        return os.getenv("INVOICE_GENIE_SPACE_ID", None) or None

    @functools.cache
    def _genie_context(self) -> tuple[genie.Service | None, str | None]:
        genie_space_id = self._genie_space_id()
        if genie_space_id:
            wc = clients.workspace_client()
            service = genie.Service(wc, genie_space_id)
            conversation_id = service.create_conversation(
                "Answer questions about invoices"
            ).conversation_id
            return service, conversation_id
        else:
            return None, None


def _broadcast_status(status: GenieStatusMessage) -> None:
    """Broadcast Genie status update via WebSocket."""
    try:
        from invoice_ui.ws_server import broadcast_genie_status

        broadcast_genie_status(status.to_dict())
    except ImportError:
        pass  # WebSocket not initialized
    except Exception as e:
        LOG.warning("Failed to broadcast Genie status: %s", e)
