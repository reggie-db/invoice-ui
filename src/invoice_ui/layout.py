import os

from dash import dcc, html
from dash_extensions import WebSocket

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.components.invoice_search import build_search_panel
from invoice_ui.models.invoice import InvoicePage, serialize_page

"""Layout helpers for the Dash app."""

# Branding configuration
_USE_GENERIC = os.getenv("INVOICE_UI_GENERIC", "false").lower() in {"1", "true", "yes"}

_BRANDING = {
    "title": "Invoice Search" if _USE_GENERIC else "Hardware Invoice Search",
    "subtitle": (
        "Search and browse invoices."
        if _USE_GENERIC
        else "Search through computer hardware orders and invoices."
    ),
}

# WebSocket path (same port as app)
_WS_PATH = "/ws/genie"


def build_layout(
    initial_page: InvoicePage,
    initial_query: str = "",
    ai_available: bool = False,
) -> html.Div:
    """
    Return the root layout for the app.

    Args:
        initial_page: Initial page of invoices to display.
        initial_query: Pre-populated search query.
        ai_available: Whether AI-powered search is available.
    """
    initial_state = serialize_page(initial_page, initial_query, scroll_token=0)

    return html.Div(
        className="app-shell",
        children=[
            dcc.Location(id="url", refresh=False),
            dcc.Download(id="download-file"),
            dcc.Store(id="invoice-state", data=initial_state),
            dcc.Store(id="scroll-trigger", data=0),
            # WebSocket for real-time status updates
            dcc.Store(id="ws-url-store", data={"path": _WS_PATH}),
            WebSocket(id="genie-ws", url=""),
            html.Div(
                className="app-container",
                children=[
                    _build_page_header(),
                    build_search_panel(initial_query, ai_available=ai_available),
                    html.Div(
                        id="results-container",
                        children=build_invoice_results(
                            initial_page, initial_query, initial_page.has_more
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
            html.H1(_BRANDING["title"]),
            html.P(_BRANDING["subtitle"]),
        ],
    )
