from __future__ import annotations

from dash import dcc, html

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.components.invoice_search import build_search_panel
from invoice_ui.models.invoice import InvoicePage, serialize_invoice

"""Layout helpers for the Dash app."""


def build_layout(initial_page: InvoicePage, initial_query: str = "") -> html.Div:
    """Return the root layout for the app."""
    initial_state = {
        "query": initial_query,
        "page": initial_page.page,
        "page_size": initial_page.page_size,
        "total": initial_page.total,
        "items": [serialize_invoice(invoice) for invoice in initial_page.items],
        "has_more": initial_page.has_more,
        "scroll_token": 0,
    }
    return html.Div(
        className="app-shell",
        children=[
            dcc.Location(id="url", refresh=False),
            dcc.Download(id="download-file"),
            dcc.Store(id="invoice-state", data=initial_state),
            dcc.Store(id="scroll-trigger", data=0),
            html.Div(
                className="app-container",
                children=[
                    _build_page_header(),
                    build_search_panel(initial_query),
                    html.Div(
                        id="results-container",
                        children=build_invoice_results(
                            initial_page.items, initial_query, initial_page.has_more
                        ),
                    ),
                ],
            ),
        ],
    )


def _build_page_header() -> html.Div:
    """Return the hero text area at the top of the page."""
    return html.Div(
        className="page-header",
        children=[
            html.H1("Hardware Invoice Search"),
            html.P("Search through computer hardware orders and invoices."),
        ],
    )
