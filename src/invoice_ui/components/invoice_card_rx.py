"""
Reflex invoice card component.

Displays a single invoice with all its details in an expandable card format.
Uses InvoiceModel for Reflex-compatible reactive data.
"""

import asyncio
import os

import reflex as rx
from reflex.event import EventSpec
from reggie_core import logs
from reggie_tools import clients

from invoice_ui.models.reflex_models import InvoiceModel, LineItemModel
from invoice_ui.utils import format_currency

LOG = logs.logger(__file__)


class DownloadState(rx.State):
    download_paths: list[str] = []

    @rx.event(background=True)
    async def download(self, path: str) -> EventSpec:
        if path in self.download_paths:
            return []

        download_path = DownloadState._download_path(path)
        filename = (
            os.path.basename(download_path) if "/" in download_path else "invoice.pdf"
        )
        async with self:
            self.download_paths.append(path)
        try:
            LOG.info("Download triggered for: %s", download_path)

            def _download_bytes() -> bytes:
                try:
                    LOG.info("Using Spark for download")
                    spark = clients.spark()
                    df = spark.read.format("binaryFile").load(f"dbfs:{download_path}")
                    row = df.collect()[0]
                    return bytes(row.content)
                except Exception:
                    LOG.warning("Spark download failed", exc_info=True)
                LOG.info("Using workspace client for download")
                workspace = clients.workspace_client()
                file_response = workspace.files.download(download_path)
                return file_response.contents.read()

            download_task = asyncio.get_running_loop().run_in_executor(
                None, _download_bytes
            )
            download_bytes = await download_task
        finally:
            async with self:
                self.download_paths.remove(path)
        return rx.download(data=download_bytes, filename=filename)

    @staticmethod
    def _download_path(path: str) -> str:
        prefix = "dbfs:"
        return path[len(prefix) :] if path.startswith(prefix) else path


def invoice_card(invoice: InvoiceModel) -> rx.Component:
    """
    Build a card component for displaying an invoice.

    Args:
        invoice: InvoiceModel instance.

    Returns:
        The invoice card component.
    """
    return rx.box(
        _build_header(invoice),
        _build_body(invoice),
        class_name="card invoice-card",
    )


def _format_date_str(date_str: str) -> str:
    """Format an ISO date string for display."""
    if False:
        if not date_str:
            return "N/A"
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%b %d, %Y")
        except (ValueError, TypeError):
            return date_str
    return date_str


def _build_header(invoice: InvoiceModel) -> rx.Component:
    """Build the card header with invoice number and metadata."""

    return rx.box(
        rx.box(
            rx.box(
                rx.icon("file-text", class_name="title-icon"),
                rx.heading(
                    f"Invoice #{invoice.invoice.invoice_number}",
                    size="3",
                    as_="h3",
                ),
                class_name="title-row",
            ),
            rx.box(
                _meta_item("calendar", _format_date_str(invoice.invoice.invoice_date)),
                _meta_item(
                    "dollar-sign",
                    format_currency(
                        invoice.invoice.amount_due.value,
                        invoice.invoice.amount_due.currency,
                    ),
                ),
                rx.text(invoice.invoice.terms, class_name="badge secondary"),
                class_name="meta-row",
            ),
            class_name="header-text",
        ),
        rx.button(
            rx.icon("download", size=16),
            "Download",
            loading=DownloadState.download_paths.contains(invoice.path),
            disabled=DownloadState.download_paths.contains(invoice.path),
            class_name="download-button",
            on_click=lambda evt: DownloadState.download(invoice.path),
            title="Download PDF",
        ),
        class_name="card-header",
    )


def _build_body(invoice: InvoiceModel) -> rx.Component:
    """Build the card body with all invoice details."""
    return rx.box(
        _build_order_details(invoice),
        rx.box(class_name="divider"),
        _build_parties(invoice),
        rx.box(class_name="divider"),
        _build_line_items(invoice),
        rx.box(class_name="divider"),
        _build_totals(invoice),
        class_name="card-body",
    )


def _build_order_details(invoice: InvoiceModel) -> rx.Component:
    """Build the order metadata grid."""
    due_date_formatted = rx.cond(
        invoice.invoice.due_date,
        _format_date_str(invoice.invoice.due_date),
        "N/A",
    )

    return rx.box(
        _info_block("Purchase Order", invoice.invoice.purchase_order_number),
        _info_block("Sales Order", invoice.invoice.sales_order_number),
        rx.box(
            rx.text("Due Date", class_name="label"),
            rx.text(due_date_formatted, class_name="value"),
            class_name="info-block",
        ),
        class_name="info-grid surface",
    )


def _build_parties(invoice: InvoiceModel) -> rx.Component:
    """Build the seller, buyer, and ship to sections."""
    return rx.box(
        _party_block(
            "Seller", "building-2", invoice.seller.name, invoice.seller.address
        ),
        _party_block("Buyer", "building-2", invoice.buyer.name, invoice.buyer.address),
        _party_block_with_attention(
            "Ship To",
            "map-pin",
            invoice.ship_to.name,
            invoice.ship_to.address,
            invoice.ship_to.attention,
        ),
        class_name="party-grid",
    )


def _build_line_items(invoice: InvoiceModel) -> rx.Component:
    """Build the collapsible line items section."""
    return rx.el.details(
        rx.el.summary(
            rx.box(
                rx.icon("package", class_name="title-icon"),
                rx.heading(
                    f"Line Items ({invoice.line_items.length()})",
                    size="2",
                    as_="h4",
                ),
                class_name="summary-header",
            ),
            rx.box(
                rx.text("Show Details", class_name="toggle-text closed"),
                rx.text("Hide Details", class_name="toggle-text open"),
                class_name="summary-toggle",
            ),
        ),
        rx.box(
            rx.foreach(
                invoice.line_items,
                lambda item: _line_item_card(item, invoice.totals.currency),
            ),
            class_name="line-items-list",
        ),
        class_name="line-items",
    )


def _line_item_card(item: LineItemModel, currency: str) -> rx.Component:
    """Build an individual line item card."""
    return rx.box(
        rx.box(
            rx.text(item.description, class_name="line-item-title"),
            rx.box(
                _info_block("MFR Part #", item.manufacturer_part_number),
                rx.box(
                    rx.text("Quantity", class_name="label"),
                    rx.text(
                        f"{item.quantity_shipped} / {item.quantity_ordered}",
                        class_name="value",
                    ),
                    class_name="info-block",
                ),
                rx.box(
                    rx.text("Unit Price", class_name="label"),
                    rx.text(
                        format_currency(item.unit_price, currency), class_name="value"
                    ),
                    class_name="info-block",
                ),
                class_name="line-item-grid",
            ),
            class_name="line-item-main",
        ),
        rx.box(
            rx.text("Extended Price", class_name="label"),
            rx.text(format_currency(item.extended_price, currency), class_name="value"),
            class_name="line-item-total",
        ),
        # Serial numbers (conditionally rendered)
        rx.cond(
            item.serial_numbers.length() > 0,
            rx.box(
                rx.text(
                    f"Serial Numbers ({item.serial_numbers.length()})",
                    class_name="label",
                ),
                rx.box(
                    rx.foreach(
                        item.serial_numbers,
                        lambda sn: rx.text(sn, class_name="badge outline mono"),
                    ),
                    class_name="badge-list",
                ),
                class_name="serial-block",
            ),
        ),
        class_name="line-item-card",
    )


def _build_totals(invoice: InvoiceModel) -> rx.Component:
    """Build the totals footer section."""
    currency = invoice.totals.currency

    return rx.box(
        _totals_row("Subtotal", invoice.totals.subtotal, currency),
        _totals_row("Shipping", invoice.totals.shipping, currency),
        _totals_row("Tax", invoice.totals.tax, currency),
        rx.box(class_name="divider subtle"),
        _totals_row("Total", invoice.totals.total, currency, emphasize=True),
        class_name="totals",
    )


def _totals_row(
    label: str, value: float, currency: str, emphasize: bool = False
) -> rx.Component:
    """Build a row within the totals section."""
    class_name = "totals-row emphasize" if emphasize else "totals-row"
    return rx.box(
        rx.text(label),
        rx.text(format_currency(value, currency)),
        class_name=class_name,
    )


def _info_block(label: str, value: str) -> rx.Component:
    """Build a small info block with label and value."""
    return rx.box(
        rx.text(label, class_name="label"),
        rx.text(value, class_name="value"),
        class_name="info-block",
    )


def _party_block(
    label: str,
    icon: str,
    name: str,
    address: list[str],
) -> rx.Component:
    """Build a party block (seller, buyer)."""
    return rx.box(
        rx.icon(icon, class_name="title-icon"),
        rx.box(
            rx.text(label, class_name="label"),
            rx.text(name, class_name="value"),
            rx.foreach(address, lambda line: rx.text(line, class_name="muted")),
        ),
        class_name="party-block",
    )


def _party_block_with_attention(
    label: str,
    icon: str,
    name: str,
    address: list[str],
    attention: str,
) -> rx.Component:
    """Build a party block with attention line (ship to)."""
    return rx.box(
        rx.icon(icon, class_name="title-icon"),
        rx.box(
            rx.text(label, class_name="label"),
            rx.text(name, class_name="value"),
            rx.cond(
                attention != "",
                rx.text(f"Attn: {attention}", class_name="muted"),
            ),
            rx.foreach(address, lambda line: rx.text(line, class_name="muted")),
        ),
        class_name="party-block",
    )


def _meta_item(icon: str, label: str) -> rx.Component:
    """Build a metadata chip with icon and label."""
    return rx.box(
        rx.icon(icon, class_name="meta-icon", size=16),
        rx.text(label),
        class_name="meta-item",
    )
