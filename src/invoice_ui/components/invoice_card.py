from __future__ import annotations

from typing import Sequence

from dash import html
from dash_iconify import DashIconify

from invoice_ui.models.invoice import Invoice, LineItem, Party, ShipTo

"""Reusable invoice card component."""


def build_invoice_card(invoice: Invoice, card_id: str | None = None) -> html.Div:
    """Return a card styled container for a specific invoice."""
    invoice_id = card_id or f"invoice-{invoice.invoice.invoice_number}"
    return html.Div(
        id=invoice_id,
        className="card invoice-card",
        children=[
            _build_header(invoice, invoice_id),
            _build_body(invoice),
        ],
    )


def _build_header(invoice: Invoice, invoice_id: str) -> html.Div:
    """Return the card header area."""
    return html.Div(
        className="card-header",
        children=[
            html.Div(
                className="header-text",
                children=[
                    html.Div(
                        className="title-row",
                        children=[
                            DashIconify(
                                icon="lucide:file-text", className="title-icon"
                            ),
                            html.H3(f"Invoice #{invoice.invoice.invoice_number}"),
                        ],
                    ),
                    html.Div(
                        className="meta-row",
                        children=[
                            _meta_item(
                                icon="lucide:calendar",
                                label=invoice.invoice.formatted_invoice_date(),
                            ),
                            _meta_item(
                                icon="lucide:dollar-sign",
                                label=f"{invoice.invoice.amount_due.currency} {invoice.invoice.amount_due.value:,.2f}",
                            ),
                            html.Span(
                                invoice.invoice.terms, className="badge secondary"
                            ),
                        ],
                    ),
                ],
            ),
            html.Button(
                id={"type": "download-button", "index": invoice_id},
                className="button primary ghost gap",
                children=[
                    DashIconify(icon="lucide:download", className="button-icon"),
                    "Download PDF",
                ],
            ),
        ],
    )


def _build_body(invoice: Invoice) -> html.Div:
    """Return the card body with all detailed sections."""
    return html.Div(
        className="card-body",
        children=[
            _build_order_details(invoice),
            html.Div(className="divider"),
            _build_parties(invoice),
            html.Div(className="divider"),
            _build_line_items(invoice.line_items, invoice.totals.currency),
            html.Div(className="divider"),
            _build_totals(invoice),
        ],
    )


def _build_order_details(invoice: Invoice) -> html.Div:
    """Return the order metadata grid."""
    return html.Div(
        className="info-grid surface",
        children=[
            _info_block("Purchase Order", invoice.invoice.purchase_order_number),
            _info_block("Sales Order", invoice.invoice.sales_order_number),
            _info_block("Due Date", invoice.invoice.formatted_due_date()),
        ],
    )


def _build_parties(invoice: Invoice) -> html.Div:
    """Return the seller, buyer, and ship to sections."""
    return html.Div(
        className="party-grid",
        children=[
            _party_block("Seller", "lucide:building-2", invoice.seller),
            _party_block("Buyer", "lucide:building-2", invoice.buyer),
            _party_block(
                "Ship To", "lucide:map-pin", invoice.ship_to, include_attention=True
            ),
        ],
    )


def _build_line_items(line_items: Sequence[LineItem], currency: str) -> html.Details:
    """Return the collapsible line item list."""
    return html.Details(
        className="line-items",
        open=False,
        children=[
            html.Summary(
                children=[
                    html.Div(
                        className="summary-header",
                        children=[
                            DashIconify(icon="lucide:package", className="title-icon"),
                            html.H4(f"Line Items ({len(line_items)})"),
                        ],
                    ),
                    html.Div(
                        className="summary-toggle",
                        children=[
                            html.Span("Show Details", className="toggle-text closed"),
                            html.Span("Hide Details", className="toggle-text open"),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="line-items-list",
                children=[_line_item_card(item, currency) for item in line_items],
            ),
        ],
    )


def _line_item_card(item: LineItem, currency: str) -> html.Div:
    """Return an individual line item card."""
    return html.Div(
        className="line-item-card",
        children=[
            html.Div(
                className="line-item-main",
                children=[
                    html.P(item.description, className="line-item-title"),
                    html.Div(
                        className="line-item-grid",
                        children=[
                            _info_block("Line #", item.line_number),
                            _info_block("MFR Part #", item.manufacturer_part_number),
                            _info_block(
                                "Quantity",
                                f"{item.quantity_shipped} / {item.quantity_ordered}",
                            ),
                            _info_block(
                                "Unit Price",
                                _format_currency(item.unit_price, currency),
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="line-item-total",
                children=[
                    html.Span("Extended Price", className="label"),
                    html.Span(
                        _format_currency(item.extended_price, currency),
                        className="value",
                    ),
                ],
            ),
            _serial_number_block(item.serial_numbers),
        ],
    )


def _serial_number_block(serial_numbers: Sequence[str]) -> html.Div | None:
    """Return badges for serial numbers when present."""
    if not serial_numbers:
        return None

    return html.Div(
        className="serial-block",
        children=[
            html.Span(f"Serial Numbers ({len(serial_numbers)})", className="label"),
            html.Div(
                className="badge-list",
                children=[
                    html.Span(sn, className="badge outline mono")
                    for sn in serial_numbers
                ],
            ),
        ],
    )


def _build_totals(invoice: Invoice) -> html.Div:
    """Return the totals footer."""
    totals = invoice.totals
    return html.Div(
        className="totals",
        children=[
            _totals_row("Subtotal", totals.subtotal, totals.currency),
            _totals_row("Shipping", totals.shipping, totals.currency),
            _totals_row("Tax", totals.tax, totals.currency),
            html.Div(className="divider subtle"),
            _totals_row("Total", totals.total, totals.currency, emphasize=True),
        ],
    )


def _totals_row(
    label: str, value: float, currency: str, emphasize: bool = False
) -> html.Div:
    """Return a row within the totals section."""
    classes = "totals-row"
    if emphasize:
        classes += " emphasize"
    return html.Div(
        className=classes,
        children=[
            html.Span(label),
            html.Span(_format_currency(value, currency)),
        ],
    )


def _info_block(label: str, value: str) -> html.Div:
    """Return a small info block."""
    return html.Div(
        className="info-block",
        children=[
            html.Span(label, className="label"),
            html.Span(value, className="value"),
        ],
    )


def _party_block(
    label: str,
    icon: str,
    party: Party | ShipTo,
    include_attention: bool = False,
) -> html.Div:
    """Return a block describing one of the parties involved in the invoice."""
    address_lines = getattr(party, "address", [])
    children = [
        html.Span(label, className="label"),
        html.Span(getattr(party, "name", ""), className="value"),
    ]
    if include_attention and hasattr(party, "attention"):
        children.append(html.Span(f"Attn: {party.attention}", className="muted"))
    children.extend(html.Span(line, className="muted") for line in address_lines)

    return html.Div(
        className="party-block",
        children=[
            DashIconify(icon=icon, className="title-icon"),
            html.Div(children=children),
        ],
    )


def _meta_item(icon: str, label: str) -> html.Span:
    """Return a metadata chip."""
    return html.Span(
        className="meta-item",
        children=[
            DashIconify(icon=icon, className="meta-icon"),
            html.Span(label),
        ],
    )


def _format_currency(value: float, currency: str) -> str:
    """Format a currency amount using the invoice currency symbol."""
    return f"{currency} {value:,.2f}"
