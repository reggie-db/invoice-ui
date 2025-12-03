from __future__ import annotations

from dash import html
from dash_iconify import DashIconify

from invoice_ui.components.invoice_card import build_invoice_card
from invoice_ui.models.invoice import InvoicePage

"""Helpers that render the invoice result list."""


def build_invoice_results(
    invoice_page: InvoicePage | None, query: str | None, has_more: bool = False
) -> html.Div:
    """Return either the empty state or the list of invoice cards."""
    invoices = invoice_page.items if invoice_page else []
    if not invoice_page or not invoices:
        return html.Div(
            className="card empty-state",
            children=[
                DashIconify(icon="lucide:file-x", className="empty-icon"),
                html.H3("No invoices found"),
                html.P(
                    _empty_state_message(query),
                    className="muted",
                ),
            ],
        )
    results_children = [
        html.Div(
            className="results-summary",
            children=[
                html.Span(
                    _summary_text(invoice_page.total, query),
                    className="muted",
                ),
            ],
        ),
        html.Div(
            className="stack",
            children=[
                build_invoice_card(invoice, f"invoice-{invoice.invoice.invoice_number}")
                for invoice in invoices
            ],
        ),
    ]

    # Loading indicator for infinite scroll
    results_children.append(
        html.Div(
            id="load-more-container",
            className="load-more-container",
            children=[
                html.Div(
                    id="load-more-hint",
                    className="load-more-hint" + ("" if has_more else " end"),
                    children="Scroll to load more"
                    if has_more
                    else "All invoices loaded",
                ),
                html.Div(
                    id="load-more-spinner",
                    className="load-more-spinner hidden",
                    children=[
                        html.Span(className="spinner"),
                        html.Span("Loading invoices...", className="loading-text"),
                    ],
                ),
            ],
        )
    )

    return html.Div(className="results", children=results_children)


def _summary_text(count: int, query: str | None) -> str:
    """Return the summary that mirrors the React implementation."""
    noun = "invoice" if count == 1 else "invoices"
    base = f"{count} {noun} found"
    if query and query.strip():
        return f'{base} for "{query.strip()}"'
    return base


def _empty_state_message(query: str | None) -> str:
    """Return context sensitive guidance for the empty state."""
    if query and query.strip():
        return f'No results match "{query.strip()}". Try a different search term.'
    return "No invoices available."
