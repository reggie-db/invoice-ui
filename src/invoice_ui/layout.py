import os

from dash import dcc, html
from dash_extensions import WebSocket

from invoice_ui.components.invoice_results import build_loading_state
from invoice_ui.components.invoice_search import build_search_panel

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


def build_layout(ai_available: bool = False) -> html.Div:
    """
    Return the root layout for the app.

    Renders immediately with a loading state. The first page of invoices
    is loaded asynchronously via the search callback.

    Args:
        ai_available: Whether AI-powered search is available.
    """
    return html.Div(
        className="app-shell",
        children=[
            dcc.Location(id="url", refresh=False),
            dcc.Download(id="download-file"),
            # Start with empty state; first load triggered by callback
            dcc.Store(id="invoice-state", data=None),
            dcc.Store(id="scroll-trigger", data=0),
            dcc.Store(id="download-path-store", data=""),
            dcc.Store(id="download-trigger", data=0),
            # Trigger for initial load (set to 1 to fire callback on mount)
            dcc.Store(id="initial-load-trigger", data=1),
            # WebSocket for real-time status updates
            dcc.Store(id="ws-url-store", data={"path": _WS_PATH}),
            WebSocket(id="genie-ws", url=""),
            html.Div(
                className="app-container",
                children=[
                    _build_page_header(),
                    build_search_panel("", ai_available=ai_available),
                    html.Div(
                        id="results-container",
                        children=build_loading_state(),
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
